import React from 'react'
import { apiService } from '../services/api'
import '../styles/components/ContentEvaluation.css'

const ContentEvaluation = ({ contentData, updateContentData, loading, setLoading }) => {

    const evaluateContent = async () => {
        if (!contentData.research_data && !contentData.approved_outline && !contentData.final_draft) {
            alert('No content available for evaluation')
            return
        }

        try {
            setLoading(true)
            const response = await apiService.evaluateContent(contentData)
            updateContentData('evaluations', response.evaluations)
        } catch (error) {
            console.error('Failed to evaluate content:', error)
            alert('Failed to evaluate content')
        } finally {
            setLoading(false)
        }
    }

    const renderScoreBar = (score, maxScore = 10) => {
        const percentage = (score / maxScore) * 100
        const getColorClass = (score) => {
            if (score >= 8) return 'excellent'
            if (score >= 6) return 'good'
            if (score >= 4) return 'fair'
            return 'poor'
        }

        return (
            <div className="score-bar">
                <div
                    className={`score-fill ${getColorClass(score)}`}
                    style={{ width: `${percentage}%` }}
                />
                <span className="score-text">{score}/10</span>
            </div>
        )
    }

    const renderEvaluationSection = (title, evaluation, criteria) => {
        if (!evaluation) return null

        const averageScore = Object.values(evaluation).reduce((sum, score) => sum + score, 0) / Object.keys(evaluation).length

        return (
            <div className="evaluation-section">
                <h4>{title}</h4>
                <div className="overall-score">
                    <strong>Overall Score: {averageScore.toFixed(1)}/10</strong>
                    {renderScoreBar(averageScore)}
                </div>

                <div className="criteria-scores">
                    {Object.entries(evaluation).map(([criterion, score]) => (
                        <div key={criterion} className="criterion">
                            <div className="criterion-header">
                                <span className="criterion-name">
                                    {criteria[criterion] || criterion.charAt(0).toUpperCase() + criterion.slice(1)}
                                </span>
                                <span className="criterion-score">{score}/10</span>
                            </div>
                            {renderScoreBar(score)}
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    const hasContent = contentData.research_data || contentData.approved_outline || contentData.final_draft
    const hasEvaluations = contentData.evaluations && Object.keys(contentData.evaluations).length > 0

    return (
        <div className="content-evaluation">
            <div className="evaluation-header">
                <h2>Content Evaluation</h2>
                <p>AI-powered evaluation of your content across multiple criteria</p>
            </div>

            {!hasContent ? (
                <div className="no-content">
                    <p>No content available for evaluation. Please create some content first.</p>
                </div>
            ) : (
                <>
                    <div className="evaluation-controls">
                        <button
                            onClick={evaluateContent}
                            disabled={loading}
                            className="btn btn-primary"
                        >
                            {hasEvaluations ? 'Re-evaluate Content' : 'Evaluate Content'}
                        </button>
                    </div>

                    {hasEvaluations && (
                        <div className="evaluations-container">
                            {renderEvaluationSection(
                                'Research Evaluation',
                                contentData.evaluations.research,
                                {
                                    depth: 'Depth of Research',
                                    relevance: 'Relevance to Topic',
                                    credibility: 'Credibility of Information'
                                }
                            )}

                            {renderEvaluationSection(
                                'Outline Evaluation',
                                contentData.evaluations.outline,
                                {
                                    flow: 'Logical Flow',
                                    completeness: 'Completeness of Coverage',
                                    clarity: 'Clarity of Structure'
                                }
                            )}

                            {renderEvaluationSection(
                                'Draft Evaluation',
                                contentData.evaluations.draft,
                                {
                                    quality: 'Overall Quality',
                                    coherence: 'Coherence & Flow',
                                    engagement: 'Reader Engagement'
                                }
                            )}

                            <div className="evaluation-summary">
                                <h3>Evaluation Summary</h3>
                                <div className="summary-grid">
                                    {Object.entries(contentData.evaluations).map(([type, evaluation]) => {
                                        const averageScore = Object.values(evaluation).reduce((sum, score) => sum + score, 0) / Object.keys(evaluation).length
                                        return (
                                            <div key={type} className="summary-card">
                                                <h4>{type.charAt(0).toUpperCase() + type.slice(1)}</h4>
                                                <div className="summary-score">
                                                    {averageScore.toFixed(1)}/10
                                                </div>
                                                {renderScoreBar(averageScore)}
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Content Preview */}
            {hasContent && (
                <div className="content-preview">
                    <h3>Current Content</h3>

                    {contentData.topic && (
                        <div className="preview-section">
                            <h4>Topic</h4>
                            <p>{contentData.topic}</p>
                        </div>
                    )}

                    {contentData.research_data && (
                        <div className="preview-section">
                            <h4>Research Data</h4>
                            <div className="preview-content">
                                {contentData.research_data.split('\n').map((line, index) => (
                                    <p key={index}>{line}</p>
                                ))}
                            </div>
                        </div>
                    )}

                    {contentData.approved_outline && (
                        <div className="preview-section">
                            <h4>Approved Outline</h4>
                            <pre className="preview-content">{contentData.approved_outline}</pre>
                        </div>
                    )}

                    {contentData.final_draft && (
                        <div className="preview-section">
                            <h4>Final Draft</h4>
                            <div className="preview-content">
                                {contentData.final_draft.split('\n').map((line, index) => (
                                    <p key={index}>{line}</p>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default ContentEvaluation
