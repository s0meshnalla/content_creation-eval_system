from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import json
import os
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
import logging
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Content Creation & Evaluation API",
    description="AI-Powered Content Generation with Human-in-the-Loop Review",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class TopicRequest(BaseModel):
    topic: str

class OutlineRequest(BaseModel):
    topic: str
    research_data: str

class DraftRequest(BaseModel):
    outline: str
    research_data: str

class RevisionRequest(BaseModel):
    draft: str
    feedback: str

class EvaluationRequest(BaseModel):
    content_data: Dict[str, Any]

class ContentSaveRequest(BaseModel):
    content_data: Dict[str, Any]

# Global variables
API_KEY = os.getenv("GOOGLE_API_KEY")
MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "4096"))

if not API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables")

# Default prompts for content generation
DEFAULT_PROMPTS = {
    "research": "You are a research assistant. Your task is to gather key information on the topic: {topic}.\nProvide 3-5 concise bullet points summarizing the most relevant facts or insights.\nUse simple language and focus on general knowledge (no external sources needed).",
    "outline": "You are a content creation assistant. Create a structured and comprehensive article outline for the topic: {topic}.\nUse this provided research: {research_data}.\nFollow this format, ensuring all key aspects from the research are covered and presented logically:\n# Article Outline\n## Introduction\n- Brief overview of the topic and its importance\n- What the reader will learn\n## Section 1: [Clear, Descriptive Section Title reflecting a core concept]\n- Key point 1 (elaborate slightly to ensure completeness)\n- Key point 2 (elaborate slightly to ensure completeness)\n## Section 2: [Clear, Descriptive Section Title reflecting another core concept]\n- Key point 1 (elaborate slightly to ensure completeness)\n- Key point 2 (elaborate slightly to ensure completeness)\n## Conclusion\n- Summary of key takeaways and their relevance\n- A concluding thought or call to action (if applicable)\nKeep it clear, logical, and concise. Use simple words for a beginner audience.",
    "draft": "You are a content writer. Write a full article based on the approved outline: {outline}.\nUse the research: {research_data}.\nWrite in a friendly, conversational tone suitable for beginners.\nEach section should be 2-3 short paragraphs (100-150 words total per section).\nInclude simple examples from daily life. Avoid technical jargon and ensure clarity.",
    "draft_revision": "You are a content writer. Revise the following article draft based on this feedback: {feedback}\nDraft: {draft}\nKeep the friendly, conversational tone suitable for beginners. Ensure the revised draft addresses the feedback while maintaining clarity and avoiding technical jargon."
}

# Evaluation prompts
EVALUATION_PROMPTS = {
    "research_evaluation": """
Rate the research quality from 1 to 10 for each criterion:

TOPIC: {topic}
RESEARCH DATA: {research_data}

Criteria:
- depth: How comprehensive and detailed (1=very shallow, 10=very comprehensive)
- relevance: How relevant to the topic (1=not relevant, 10=highly relevant)
- credibility: How trustworthy the information (1=questionable, 10=very credible)

Respond with only this JSON format:
{{"depth": 8, "relevance": 9, "credibility": 7}}
""",
    
    "outline_evaluation": """
Rate the outline quality from 1 to 10 for each criterion:

OUTLINE: {outline}

Criteria:
- flow: Logical progression of ideas (1=confusing, 10=excellent flow)
- completeness: Coverage of the topic (1=missing key points, 10=comprehensive)
- clarity: Structure clarity (1=unclear, 10=very clear)

Respond with only this JSON format:
{{"flow": 8, "completeness": 9, "clarity": 7}}
""",
    
    "draft_evaluation": """
Rate the draft quality from 1 to 10 for each criterion:

DRAFT: {draft}

Criteria:
- quality: Overall writing quality (1=poor, 10=excellent)
- coherence: Ideas flow together (1=disconnected, 10=very coherent)
- engagement: Reader interest level (1=boring, 10=very engaging)

Respond with only this JSON format:
{{"quality": 8, "coherence": 9, "engagement": 7}}
"""
}


DEFAULT_PROMPTS.update(EVALUATION_PROMPTS)

# EVALUATION HELPER FUNCTIONS

def get_evaluation_keywords(evaluation_type: str) -> list:
    """Get the expected keywords for each evaluation type"""
    keywords_map = {
        "research": ["depth", "relevance", "credibility"],
        "outline": ["flow", "completeness", "clarity"],
        "draft": ["quality", "coherence", "engagement"]
    }
    return keywords_map.get(evaluation_type, ["depth", "relevance", "credibility"])

def get_default_scores(evaluation_type: str) -> Dict[str, int]:
    """Return reasonable default scores when evaluation fails"""
    defaults = {
        "research": {"depth": 6, "relevance": 7, "credibility": 6},
        "outline": {"flow": 6, "completeness": 7, "clarity": 6},
        "draft": {"quality": 6, "coherence": 6, "engagement": 6}
    }
    return defaults.get(evaluation_type, {"depth": 6, "relevance": 6, "credibility": 6})

def validate_evaluation_result(result: Dict, evaluation_type: str) -> bool:
    """Validate that the evaluation result has the correct structure"""
    if not isinstance(result, dict):
        return False
    
    expected_keys = get_evaluation_keywords(evaluation_type)
    
    # Check if all expected keys are present
    if not all(key in result for key in expected_keys):
        return False
    
    # Check if all values are integers between 1 and 10
    for key in expected_keys:
        value = result[key]
        if not isinstance(value, (int, float)) or not (1 <= int(value) <= 10):
            return False
    
    return True

def clean_response_text(text: str) -> str:
    """Clean common formatting issues in Gemini responses"""
    # Remove markdown code blocks
    text = re.sub(r'\n?```', '', text)
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove any leading/trailing non-JSON text
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0 and end > start:
        text = text[start:end]
    
    return text

def extract_scores_by_keywords(text: str, evaluation_type: str) -> Dict[str, int]:
    """Extract scores by looking for keyword-score pairs when JSON parsing fails"""
    keywords = get_evaluation_keywords(evaluation_type)
    result = {}
    
    for keyword in keywords:
        # Look for patterns like "depth": 8 or "depth" : 8 or depth: 8
        patterns = [
            rf'"{keyword}"\s*:\s*(\d+)',
            rf"'{keyword}'\s*:\s*(\d+)",
            rf'{keyword}\s*:\s*(\d+)',
            rf'{keyword}.*?(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 1 <= score <= 10:
                    result[keyword] = score
                    break
    
    # If we found all required keywords, return the result
    if len(result) == len(keywords):
        return result
    
    return None

def extract_json_from_response(raw_text: str, evaluation_type: str) -> Dict[str, int]:
    """Multiple strategies to extract JSON from Gemini response"""
    if not raw_text:
        return None
    
    # Strategy 1: Clean and parse direct JSON
    try:
        cleaned = clean_response_text(raw_text)
        if cleaned.startswith('{') and cleaned.endswith('}'):
            return json.loads(cleaned)
    except:
        pass
    
    # Strategy 2: Extract JSON using regex patterns
    json_patterns = [
        r'\{[^{}]*\}',  # Simple JSON object
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, raw_text, re.DOTALL)
        for match in matches:
            try:
                cleaned_match = clean_response_text(match)
                result = json.loads(cleaned_match)
                if validate_evaluation_result(result, evaluation_type):
                    return result
            except:
                continue
    
    # Strategy 3: Extract scores using keyword patterns
    return extract_scores_by_keywords(raw_text, evaluation_type)


# GEMINI API FUNCTIONS


# Load prompts from file or use defaults
def load_prompts():
    try:
        if os.path.exists("prompt.json"):
            with open("prompt.json", "r") as f:
                loaded_prompts = json.load(f)
                # Merge with evaluation prompts
                loaded_prompts.update(EVALUATION_PROMPTS)
                return loaded_prompts
        return DEFAULT_PROMPTS
    except Exception as e:
        logger.error(f"Error loading prompts: {str(e)}")
        return DEFAULT_PROMPTS

# Standard Gemini API call for content generation
async def call_gemini(prompt: str, model: str = "gemini-2.5-flash-preview-05-20"):
    try:
        if not API_KEY:
            raise ValueError("Google API Key not configured")
        
        genai.configure(api_key=API_KEY)
        model_instance = genai.GenerativeModel(model)
        response = await model_instance.generate_content_async(
            contents=prompt,
            generation_config={"max_output_tokens": MAX_TOKENS}
        )
        return response.text if response.text else ""
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI model error: {str(e)}")

# Enhanced Gemini API call specifically for evaluations
async def call_gemini_evaluation(prompt: str, evaluation_type: str, model: str = "gemini-1.5-flash-latest"):
    """Robust evaluation function that handles malformed JSON responses from Gemini"""
    try:
        if not API_KEY:
            raise ValueError("Google API Key not configured")
        
        genai.configure(api_key=API_KEY)
        model_instance = genai.GenerativeModel(model)
        
        # Enhanced prompt with very explicit JSON instructions
        enhanced_prompt = f"""
{prompt}

CRITICAL INSTRUCTIONS:
- Respond with ONLY a valid JSON object
- Use integer scores between 1 and 10
- NO markdown, NO explanations, NO extra text
- Example format: {{"depth": 8, "relevance": 7, "credibility": 6}}
"""
        
        response = await model_instance.generate_content_async(
            contents=enhanced_prompt,
            generation_config={
                "max_output_tokens": 500,
                "temperature": 0.0,  # Maximum determinism
                "top_p": 0.1,
                "candidate_count": 1
            }
        )
        
        raw_response = response.text
        logger.info(f"Raw Gemini response for {evaluation_type}: {repr(raw_response)}")
        
        # Multiple strategies to extract valid JSON
        json_result = extract_json_from_response(raw_response, evaluation_type)
        
        if json_result:
            logger.info(f"Successfully parsed {evaluation_type} evaluation: {json_result}")
            return json_result
        else:
            raise ValueError("Could not extract valid JSON from response")
            
    except Exception as e:
        logger.error(f"Evaluation failed for {evaluation_type}: {str(e)}")
        return get_default_scores(evaluation_type)


# FILE OPERATIONS


def save_content_data(data: Dict, filename: str = "content_output.json"):
    try:
        # Add timestamp
        data["last_saved"] = datetime.now().isoformat()
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")
        return False

def load_content_data(filename: str = "content_output.json"):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return {}


# API ROUTES


@app.get("/")
async def root():
    return {"message": "Content Creation & Evaluation API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "max_tokens": MAX_TOKENS
    }


# CONTENT GENERATION ROUTES


@app.post("/api/generate-research")
async def generate_research(request: TopicRequest):
    try:
        prompts = load_prompts()
        prompt = prompts["research"].format(topic=request.topic)
        research_data = await call_gemini(prompt)
        
        if not research_data:
            raise HTTPException(status_code=500, detail="Failed to generate research data")
        
        return {"research_data": research_data}
    except Exception as e:
        logger.error(f"Error in generate_research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-outline")
async def generate_outline(request: OutlineRequest):
    try:
        prompts = load_prompts()
        prompt = prompts["outline"].format(
            topic=request.topic,
            research_data=request.research_data
        )
        outline = await call_gemini(prompt)
        
        if not outline:
            raise HTTPException(status_code=500, detail="Failed to generate outline")
        
        return {"outline": outline}
    except Exception as e:
        logger.error(f"Error in generate_outline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-draft")
async def generate_draft(request: DraftRequest):
    try:
        prompts = load_prompts()
        prompt = prompts["draft"].format(
            outline=request.outline,
            research_data=request.research_data
        )
        draft = await call_gemini(prompt)
        
        if not draft:
            raise HTTPException(status_code=500, detail="Failed to generate draft")
        
        return {"draft": draft}
    except Exception as e:
        logger.error(f"Error in generate_draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/revise-draft")
async def revise_draft(request: RevisionRequest):
    try:
        prompts = load_prompts()
        prompt = prompts["draft_revision"].format(
            draft=request.draft,
            feedback=request.feedback
        )
        revised_draft = await call_gemini(prompt)
        
        if not revised_draft:
            raise HTTPException(status_code=500, detail="Failed to revise draft")
        
        return {"revised_draft": revised_draft}
    except Exception as e:
        logger.error(f"Error in revise_draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# EVALUATION ROUTE


@app.post("/api/evaluate-content")
async def evaluate_content(request: EvaluationRequest):
    try:
        evaluations = {}
        content_data = request.content_data
        
        # Evaluate research
        if content_data.get("research_data"):
            research_prompt = EVALUATION_PROMPTS["research_evaluation"].format(
                topic=content_data.get("topic", ""),
                research_data=content_data.get("research_data", "")
            )
            evaluations["research"] = await call_gemini_evaluation(
                research_prompt, "research"
            )
        
        # Evaluate outline
        if content_data.get("approved_outline"):
            outline_prompt = EVALUATION_PROMPTS["outline_evaluation"].format(
                outline=content_data.get("approved_outline", "")
            )
            evaluations["outline"] = await call_gemini_evaluation(
                outline_prompt, "outline"
            )
        
        # Evaluate draft
        if content_data.get("final_draft"):
            draft_prompt = EVALUATION_PROMPTS["draft_evaluation"].format(
                draft=content_data.get("final_draft", "")
            )
            evaluations["draft"] = await call_gemini_evaluation(
                draft_prompt, "draft"
            )
        
        if not evaluations:
            raise HTTPException(status_code=400, detail="No content available for evaluation")
        
        logger.info(f"Final evaluations: {evaluations}")
        return {"evaluations": evaluations}
        
    except Exception as e:
        logger.error(f"Error in evaluate_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# DATA PERSISTENCE ROUTES


@app.post("/api/save-content")
async def save_content(request: ContentSaveRequest):
    try:
        success = save_content_data(request.content_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save content")
        
        return {"message": "Content saved successfully", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in save_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/load-content")
async def load_content():
    try:
        content_data = load_content_data()
        return {"content_data": content_data}
    except Exception as e:
        logger.error(f"Error in load_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# PROMPT MANAGEMENT ROUTES


@app.get("/api/prompts")
async def get_prompts():
    try:
        prompts = load_prompts()
        return {"prompts": prompts}
    except Exception as e:
        logger.error(f"Error in get_prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-prompts")
async def update_prompts(prompts: Dict[str, str]):
    try:
        # Merge with evaluation prompts to ensure they're not overwritten
        updated_prompts = {**prompts, **EVALUATION_PROMPTS}
        with open("prompt.json", "w") as f:
            json.dump(updated_prompts, f, indent=2)
        return {"message": "Prompts updated successfully"}
    except Exception as e:
        logger.error(f"Error in update_prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ERROR HANDLERS


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
    )


# MAIN ENTRY POINT


if __name__ == "__main__":
    import uvicorn
    
    # Check if API key is configured
    if not API_KEY:
        print("Warning: GOOGLE_API_KEY not found in environment variables")
        print("Please create a .env file with your Google API key:")
        print("GOOGLE_API_KEY=your_api_key_here")
        print("GEMINI_MAX_TOKENS=4096  # Optional: defaults to 4096")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
