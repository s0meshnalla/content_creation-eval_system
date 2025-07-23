import React, { useState } from 'react'
import { apiService } from '../services/api'
import '../styles/components/ContentCreation.css'

const ContentCreation = ({ contentData, updateContentData, onSave, loading, setLoading }) => {
    const [currentStep, setCurrentStep] = useState(1)
    const [feedback, setFeedback] = useState('')

    const generateResearch = async () => {
        if (!contentData.topic.trim()) {
            alert('Please enter a topic first')
            return
        }

        try {
            setLoading(true)
            const response = await apiService.generateResearch(contentData.topic)
            updateContentData('research_data', response.research_data)
            setCurrentStep(2)
        } catch (error) {
            console.error('Failed to generate research:', error)
            alert('Failed to generate research')
        } finally {
            setLoading(false)
        }
    }

    const generateOutline = async () => {
        if (!contentData.research_data.trim()) {
            alert('Research data is required to generate outline')
            return
        }

        try {
            setLoading(true)
            const response = await apiService.generateOutline(contentData.topic, contentData.research_data)
            updateContentData('outline', response.outline)
            setCurrentStep(3)
        } catch (error) {
            console.error('Failed to generate outline:', error)
            alert('Failed to generate outline')
        } finally {
            setLoading(false)
        }
    }

    const approveOutline = () => {
        if (!contentData.outline.trim()) {
            alert('No outline available to approve')
            return
        }
        updateContentData('approved_outline', contentData.outline)
        setCurrentStep(4)
    }

    const generateDraft = async () => {
        if (!contentData.approved_outline.trim()) {
            alert('Approved outline is required to generate draft')
            return
        }

        try {
            setLoading(true)
            const response = await apiService.generateDraft(contentData.approved_outline, contentData.research_data)
            updateContentData('draft', response.draft)
            setCurrentStep(5)
        } catch (error) {
            console.error('Failed to generate draft:', error)
            alert('Failed to generate draft')
        } finally {
            setLoading(false)
        }
    }

    const reviseDraft = async () => {
        if (!feedback.trim()) {
            alert('Please provide feedback for revision')
            return
        }

        try {
            setLoading(true)
            const response = await apiService.reviseDraft(contentData.draft, feedback)
            updateContentData('draft', response.revised_draft)
            setFeedback('')
        } catch (error) {
            console.error('Failed to revise draft:', error)
            alert('Failed to revise draft')
        } finally {
            setLoading(false)
        }
    }

    const finalizeDraft = () => {
        if (!contentData.draft.trim()) {
            alert('No draft available to finalize')
            return
        }
        updateContentData('final_draft', contentData.draft)
        setCurrentStep(6)
    }

    const resetWorkflow = () => {
        setCurrentStep(1)
        setFeedback('')
    }

    return (
        <div className="content-creation">
            <div className="workflow-steps">
                <div className={`step ${currentStep >= 1 ? 'active' : ''}`}>1. Topic</div>
                <div className={`step ${currentStep >= 2 ? 'active' : ''}`}>2. Research</div>
                <div className={`step ${currentStep >= 3 ? 'active' : ''}`}>3. Outline</div>
                <div className={`step ${currentStep >= 4 ? 'active' : ''}`}>4. Review</div>
                <div className={`step ${currentStep >= 5 ? 'active' : ''}`}>5. Draft</div>
                <div className={`step ${currentStep >= 6 ? 'active' : ''}`}>6. Final</div>
            </div>

            <div className="creation-sections">
                {/* Topic Input */}
                <section className="section">
                    <h3>1. Enter Topic</h3>
                    <input
                        type="text"
                        value={contentData.topic}
                        onChange={(e) => updateContentData('topic', e.target.value)}
                        placeholder="Enter your content topic..."
                        className="topic-input"
                        disabled={loading}
                    />
                    <button
                        onClick={generateResearch}
                        disabled={loading || !contentData.topic.trim()}
                        className="btn btn-primary"
                    >
                        Generate Research
                    </button>
                </section>

                {/* Research Data */}
                {contentData.research_data && (
                    <section className="section">
                        <h3>2. Research Data</h3>
                        <textarea
                            value={contentData.research_data}
                            onChange={(e) => updateContentData('research_data', e.target.value)}
                            rows={6}
                            className="textarea"
                            disabled={loading}
                        />
                        <button
                            onClick={generateOutline}
                            disabled={loading}
                            className="btn btn-primary"
                        >
                            Generate Outline
                        </button>
                    </section>
                )}

                {/* Outline */}
                {contentData.outline && (
                    <section className="section">
                        <h3>3. Article Outline</h3>
                        <textarea
                            value={contentData.outline}
                            onChange={(e) => updateContentData('outline', e.target.value)}
                            rows={10}
                            className="textarea"
                            disabled={loading}
                        />
                        <div className="button-group">
                            <button
                                onClick={approveOutline}
                                disabled={loading}
                                className="btn btn-success"
                            >
                                Approve Outline
                            </button>
                            <button
                                onClick={generateOutline}
                                disabled={loading}
                                className="btn btn-secondary"
                            >
                                Regenerate
                            </button>
                        </div>
                    </section>
                )}

                {/* Draft Generation */}
                {contentData.approved_outline && currentStep >= 4 && (
                    <section className="section">
                        <h3>4. Generate Draft</h3>
                        <div className="approved-outline">
                            <strong>Approved Outline:</strong>
                            <pre>{contentData.approved_outline}</pre>
                        </div>
                        <button
                            onClick={generateDraft}
                            disabled={loading}
                            className="btn btn-primary"
                        >
                            Generate Draft
                        </button>
                    </section>
                )}

                {/* Draft Review */}
                {contentData.draft && (
                    <section className="section">
                        <h3>5. Article Draft</h3>
                        <textarea
                            value={contentData.draft}
                            onChange={(e) => updateContentData('draft', e.target.value)}
                            rows={15}
                            className="textarea"
                            disabled={loading}
                        />

                        <div className="revision-section">
                            <h4>Provide Feedback for Revision</h4>
                            <textarea
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                placeholder="Enter your feedback for revision..."
                                rows={4}
                                className="textarea"
                                disabled={loading}
                            />
                            <div className="button-group">
                                <button
                                    onClick={reviseDraft}
                                    disabled={loading || !feedback.trim()}
                                    className="btn btn-warning"
                                >
                                    Revise Draft
                                </button>
                                <button
                                    onClick={finalizeDraft}
                                    disabled={loading}
                                    className="btn btn-success"
                                >
                                    Finalize Draft
                                </button>
                            </div>
                        </div>
                    </section>
                )}

                {/* Final Content */}
                {contentData.final_draft && (
                    <section className="section">
                        <h3>6. Final Content</h3>
                        <div className="final-content">
                            <pre>{contentData.final_draft}</pre>
                        </div>
                        <div className="button-group">
                            <button
                                onClick={onSave}
                                disabled={loading}
                                className="btn btn-primary"
                            >
                                Save Content
                            </button>
                            <button
                                onClick={resetWorkflow}
                                className="btn btn-secondary"
                            >
                                Start Over
                            </button>
                        </div>
                    </section>
                )}
            </div>
        </div>
    )
}

export default ContentCreation
