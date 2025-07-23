import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import ContentCreation from './components/ContentCreation'
import ContentEvaluation from './components/ContentEvaluation'
import LoadingSpinner from './components/LoadingSpinner'
import { apiService } from './services/api'
import './styles/App.css'

function App() {
  const [contentData, setContentData] = useState({
    topic: '',
    research_data: '',
    outline: '',
    approved_outline: '',
    draft: '',
    final_draft: '',
    evaluations: {}
  })
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('creation')

  useEffect(() => {
    loadSavedContent()
  }, [])

  const loadSavedContent = async () => {
    try {
      setLoading(true)
      const response = await apiService.loadContent()
      if (response.content_data && Object.keys(response.content_data).length > 0) {
        setContentData(response.content_data)
      }
    } catch (error) {
      console.error('Failed to load saved content:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveContent = async () => {
    try {
      setLoading(true)
      await apiService.saveContent(contentData)
      alert('Content saved successfully!')
    } catch (error) {
      console.error('Failed to save content:', error)
      alert('Failed to save content')
    } finally {
      setLoading(false)
    }
  }

  const updateContentData = (key, value) => {
    setContentData(prev => ({
      ...prev,
      [key]: value
    }))
  }

  return (
    <div className="app">
      <Header />

      <div className="container">
        <div className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'creation' ? 'active' : ''}`}
            onClick={() => setActiveTab('creation')}
          >
            Content Creation
          </button>
          <button
            className={`tab-button ${activeTab === 'evaluation' ? 'active' : ''}`}
            onClick={() => setActiveTab('evaluation')}
          >
            Content Evaluation
          </button>
        </div>

        {loading && <LoadingSpinner />}

        <div className="tab-content">
          {activeTab === 'creation' && (
            <ContentCreation
              contentData={contentData}
              updateContentData={updateContentData}
              onSave={saveContent}
              loading={loading}
              setLoading={setLoading}
            />
          )}

          {activeTab === 'evaluation' && (
            <ContentEvaluation
              contentData={contentData}
              updateContentData={updateContentData}
              loading={loading}
              setLoading={setLoading}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
