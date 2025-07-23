const API_BASE_URL = 'http://localhost:8000'

class ApiService {
    async makeRequest(endpoint, method = 'GET', data = null) {
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        }

        if (data) {
            config.body = JSON.stringify(data)
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, config)

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Network error' }))
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
        }

        return await response.json()
    }

    // Health check
    async healthCheck() {
        return this.makeRequest('/api/health')
    }

    // Content generation endpoints
    async generateResearch(topic) {
        return this.makeRequest('/api/generate-research', 'POST', { topic })
    }

    async generateOutline(topic, research_data) {
        return this.makeRequest('/api/generate-outline', 'POST', { topic, research_data })
    }

    async generateDraft(outline, research_data) {
        return this.makeRequest('/api/generate-draft', 'POST', { outline, research_data })
    }

    async reviseDraft(draft, feedback) {
        return this.makeRequest('/api/revise-draft', 'POST', { draft, feedback })
    }

    // Evaluation endpoint
    async evaluateContent(content_data) {
        return this.makeRequest('/api/evaluate-content', 'POST', { content_data })
    }

    // Data persistence endpoints
    async saveContent(content_data) {
        return this.makeRequest('/api/save-content', 'POST', { content_data })
    }

    async loadContent() {
        return this.makeRequest('/api/load-content')
    }

    // Prompt management endpoints
    async getPrompts() {
        return this.makeRequest('/api/prompts')
    }

    async updatePrompts(prompts) {
        return this.makeRequest('/api/update-prompts', 'POST', prompts)
    }
}

export const apiService = new ApiService()
