import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { FileText, Plus, AlertCircle, HelpCircle, AlertTriangle, Image as ImageIcon, X } from 'lucide-react'
import './JournalistNotes.css'

function JournalistNotes({ projectId }) {
  const [notes, setNotes] = useState([])
  const [activeNoteId, setActiveNoteId] = useState(null)
  const [activeNote, setActiveNote] = useState(null)
  const [noteTitle, setNoteTitle] = useState('')
  const [noteBody, setNoteBody] = useState('')
  const [noteCategory, setNoteCategory] = useState('raw')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState(null) // 'saving', 'saved', 'error'
  const [images, setImages] = useState([])
  const [imageUrls, setImageUrls] = useState({}) // Map image_id -> blob URL
  const [selectedImage, setSelectedImage] = useState(null)
  const [pasteFeedback, setPasteFeedback] = useState(false)
  
  const categoryOptions = [
    { value: 'raw', label: 'Råanteckning' },
    { value: 'work', label: 'Arbetsanteckning' },
    { value: 'reflection', label: 'Reflektion' },
    { value: 'question', label: 'Fråga' },
    { value: 'source', label: 'Källa' },
    { value: 'other', label: 'Övrigt' }
  ]
  
  const textareaRef = useRef(null)
  const imageInputRef = useRef(null)
  const saveTimeoutRef = useRef(null)

  const username = 'admin'
  const password = 'password'
  const auth = btoa(`${username}:${password}`)

  // Fetch notes list
  const fetchNotes = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/journalist-notes`, {
        headers: { 'Authorization': `Basic ${auth}` },
        credentials: 'omit'
      })
      if (!response.ok) throw new Error('Failed to fetch notes')
      const data = await response.json()
      setNotes(data)
      
      // Only auto-select first note if no note is currently active
      // Don't change selection if user has explicitly selected a note
      if (!activeNoteId && data.length > 0) {
        setActiveNoteId(data[0].id)
      }
    } catch (err) {
      console.error('Error fetching notes:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId, auth]) // Removed activeNoteId from dependencies to avoid loop

  // Fetch single note with body
  const fetchNote = useCallback(async (noteId) => {
    try {
      // Cleanup old blob URLs
      setImageUrls(prevUrls => {
        Object.values(prevUrls).forEach(url => {
          if (url && url.startsWith('blob:')) {
            URL.revokeObjectURL(url)
          }
        })
        return {}
      })
      
      const [noteResponse, imagesResponse] = await Promise.all([
        fetch(`http://localhost:8000/api/journalist-notes/${noteId}`, {
          headers: { 'Authorization': `Basic ${auth}` },
          credentials: 'omit'
        }),
        fetch(`http://localhost:8000/api/journalist-notes/${noteId}/images`, {
          headers: { 'Authorization': `Basic ${auth}` },
          credentials: 'omit'
        })
      ])
      
      if (!noteResponse.ok) throw new Error('Failed to fetch note')
      const noteData = await noteResponse.json()
      setActiveNote(noteData)
      setNoteTitle(noteData.title || '')
      setNoteBody(noteData.body || '')
      setNoteCategory(noteData.category || 'raw')
      
      // Fetch images
      if (imagesResponse.ok) {
        const imagesData = await imagesResponse.json()
        setImages(imagesData)
        
        // Load images with auth and create blob URLs
        const urlMap = {}
        for (const image of imagesData) {
          try {
            const imgResponse = await fetch(`http://localhost:8000/api/journalist-notes/${noteId}/images/${image.id}`, {
              headers: { 'Authorization': `Basic ${auth}` },
              credentials: 'omit'
            })
            if (imgResponse.ok) {
              const blob = await imgResponse.blob()
              urlMap[image.id] = URL.createObjectURL(blob)
            }
          } catch (err) {
            console.error(`Error loading image ${image.id}:`, err)
          }
        }
        setImageUrls(urlMap)
      } else {
        setImages([])
        setImageUrls({})
      }
    } catch (err) {
      console.error('Error fetching note:', err)
    }
  }, [auth])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  useEffect(() => {
    if (activeNoteId) {
      fetchNote(activeNoteId)
    } else {
      setActiveNote(null)
      setNoteTitle('')
      setNoteBody('')
      setNoteCategory('raw')
      setImages([])
      setImageUrls({})
    }
    
  }, [activeNoteId, fetchNote])
  
  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      setImageUrls(prevUrls => {
        Object.values(prevUrls).forEach(url => {
          if (url && url.startsWith('blob:')) {
            URL.revokeObjectURL(url)
          }
        })
        return {}
      })
    }
  }, [])

  // Autosave with debounce
  useEffect(() => {
    if (!activeNoteId) return
    
    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    // Set new timeout (2 seconds)
    saveTimeoutRef.current = setTimeout(async () => {
      await saveNote()
    }, 2000)
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [noteBody, noteTitle, noteCategory, activeNoteId])

  const saveNote = async (manual = false) => {
    if (!activeNoteId) return
    
    setSaving(true)
    setSaveStatus('saving')
    
    try {
      const response = await fetch(`http://localhost:8000/api/journalist-notes/${activeNoteId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          title: noteTitle || null,
          body: noteBody,
          category: noteCategory
        }),
        credentials: 'omit' // Prevent browser from showing native auth popup
      })
      
      if (!response.ok) throw new Error('Failed to save note')
      
      setSaveStatus('saved')
      // Show saved status longer if manually saved
      setTimeout(() => setSaveStatus(null), manual ? 3000 : 2000)
      
      // Refresh notes list to update preview (but preserve activeNoteId)
      const currentActiveId = activeNoteId
      await fetchNotes()
      // Ensure activeNoteId is preserved after refresh
      if (currentActiveId) {
        setActiveNoteId(currentActiveId)
      }
      // Refresh note to get updated timestamp
      await fetchNote(activeNoteId)
    } catch (err) {
      console.error('Error saving note:', err)
      setSaveStatus('error')
      setTimeout(() => setSaveStatus(null), 3000)
    } finally {
      setSaving(false)
    }
  }
  
  const handleManualSave = async () => {
    await saveNote(manual=true)
  }

  const createNote = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/journalist-notes`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          title: null,
          body: '',
          category: 'raw'
        }),
        credentials: 'omit' // Prevent browser from showing native auth popup
      })
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Autentisering misslyckades. Kontrollera dina inloggningsuppgifter.')
        }
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Kunde inte skapa anteckning')
      }
      
      const newNote = await response.json()
      setActiveNoteId(newNote.id)
      await fetchNotes()
    } catch (err) {
      console.error('Error creating note:', err)
      alert(err.message || 'Kunde inte skapa anteckning')
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    
    // Get plain text from clipboard
    const pastedText = e.clipboardData.getData('text/plain')
    
    // Check for images in clipboard
    const items = Array.from(e.clipboardData.items)
    const imageItem = items.find(item => item.type.startsWith('image/'))
    
    if (imageItem) {
      // Handle image paste
      const file = imageItem.getAsFile()
      if (file && activeNoteId) {
        uploadImage(file)
      }
    } else if (pastedText) {
      // Handle text paste
      const textarea = textareaRef.current
      if (!textarea) return
      
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const text = noteBody
      
      const newText = text.substring(0, start) + pastedText + text.substring(end)
      setNoteBody(newText)
      
      // Set cursor position after pasted text
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + pastedText.length
        textarea.focus()
      }, 0)
      
      // Show visual feedback
      setPasteFeedback(true)
      setTimeout(() => setPasteFeedback(false), 500)
    }
  }

  const insertPrefix = (prefix) => {
    const textarea = textareaRef.current
    if (!textarea) return
    
    const start = textarea.selectionStart
    const text = noteBody
    const lineStart = text.lastIndexOf('\n', start - 1) + 1
    const lineEnd = text.indexOf('\n', start)
    const lineEndPos = lineEnd === -1 ? text.length : lineEnd
    
    const currentLine = text.substring(lineStart, lineEndPos)
    const newLine = currentLine.startsWith(prefix) 
      ? currentLine.substring(prefix.length).trim()
      : `${prefix} ${currentLine.trim()}`
    
    const newText = text.substring(0, lineStart) + newLine + text.substring(lineEndPos)
    setNoteBody(newText)
    
    // Set cursor position
    setTimeout(() => {
      const newPos = lineStart + newLine.length
      textarea.selectionStart = textarea.selectionEnd = newPos
      textarea.focus()
    }, 0)
  }

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (file && activeNoteId) {
      uploadImage(file)
    }
    // Reset input
    if (imageInputRef.current) {
      imageInputRef.current.value = ''
    }
  }

  const uploadImage = async (file) => {
    if (!activeNoteId) return
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('Bilden är för stor. Maximal storlek är 10MB')
      return
    }
    
    // Validate image type
    if (!file.type.startsWith('image/')) {
      alert('Filen måste vara en bild')
      return
    }
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`http://localhost:8000/api/journalist-notes/${activeNoteId}/images`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`
        },
        body: formData,
        credentials: 'omit' // Prevent browser from showing native auth popup
      })
      
      if (!response.ok) throw new Error('Failed to upload image')
      
      const imageData = await response.json()
      
      // Refresh note to get updated images list
      await fetchNote(activeNoteId)
      
      // Also refresh notes list to update preview
      await fetchNotes()
    } catch (err) {
      console.error('Error uploading image:', err)
      alert('Kunde inte ladda upp bild: ' + err.message)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('sv-SE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return <div className="journalist-notes-page">Laddar...</div>
  }

  return (
    <div className="journalist-notes-page">
      <div className="journalist-notes-layout">
        {/* Left Column: Notes List */}
        <div className="notes-list-column">
          <div className="notes-list-header">
            <h3 className="notes-list-title">Anteckningar</h3>
            {notes.length > 0 && (
              <button 
                className="btn-create-note"
                onClick={createNote}
                title="Ny anteckning"
              >
                <Plus size={16} />
              </button>
            )}
          </div>
          
          <div className="notes-list">
            {notes.length === 0 ? (
              <div className="notes-empty">
                <p>Inga anteckningar ännu</p>
              </div>
            ) : (
              notes.map(note => (
                <div
                  key={note.id}
                  className={`note-item ${activeNoteId === note.id ? 'active' : ''}`}
                  onClick={() => setActiveNoteId(note.id)}
                >
                  <div className="note-item-header">
                    {note.title && (
                      <div className="note-item-title">{note.title}</div>
                    )}
                    <div className="note-item-preview">
                      {note.preview || '(Tom anteckning)'}
                    </div>
                  </div>
                  <div className="note-item-meta">
                    <span className="note-item-category">{categoryOptions.find(c => c.value === note.category)?.label || note.category}</span>
                    <span className="note-item-date">{formatDate(note.updated_at || note.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Editor */}
        <div className="notes-editor-column">
          {activeNote ? (
            <>
              <div className="editor-header">
                <div className="editor-header-left">
                  <h3 className="editor-title">Redigera anteckning</h3>
                  {saveStatus && (
                    <span className={`save-status save-status-${saveStatus}`}>
                      {saveStatus === 'saving' && 'Sparas...'}
                      {saveStatus === 'saved' && 'Sparad'}
                      {saveStatus === 'error' && 'Fel vid sparande'}
                    </span>
                  )}
                </div>
                <div className="editor-header-meta">
                  <span className="editor-date-info">
                    {saveStatus === 'saved' ? (
                      <>✓ Sparad {formatDate(activeNote.updated_at)}</>
                    ) : (
                      <>Skapad: {formatDate(activeNote.created_at)} • Uppdaterad: {formatDate(activeNote.updated_at)}</>
                    )}
                  </span>
                </div>
                <div className="editor-header-actions">
                  <button
                    className="btn-save-note"
                    onClick={handleManualSave}
                    disabled={saving}
                    title="Spara anteckning"
                  >
                    {saving ? (
                      <>
                        <span className="save-spinner"></span>
                        <span>Sparar...</span>
                      </>
                    ) : (
                      <>
                        <span>💾</span>
                        <span>Spara</span>
                      </>
                    )}
                  </button>
                  <input
                    ref={imageInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    style={{ display: 'none' }}
                  />
                  <button
                    className="btn-editor-action"
                    onClick={() => imageInputRef.current?.click()}
                    title="Ladda upp bild"
                  >
                    <ImageIcon size={16} />
                  </button>
                </div>
              </div>

              <div className="editor-title-section">
                <input
                  type="text"
                  className="editor-title-input"
                  placeholder="Titel på anteckningen (valfritt)"
                  value={noteTitle}
                  onChange={(e) => setNoteTitle(e.target.value)}
                />
                <select
                  className="editor-category-select"
                  value={noteCategory}
                  onChange={(e) => setNoteCategory(e.target.value)}
                >
                  {categoryOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="editor-prefix-buttons">
                <button
                  className="btn-prefix"
                  onClick={() => insertPrefix('❗')}
                  title="Viktigt"
                >
                  <AlertCircle size={14} />
                  <span>Viktigt</span>
                </button>
                <button
                  className="btn-prefix"
                  onClick={() => insertPrefix('❓')}
                  title="Fråga"
                >
                  <HelpCircle size={14} />
                  <span>Fråga</span>
                </button>
                <button
                  className="btn-prefix"
                  onClick={() => insertPrefix('⚠️')}
                  title="Osäkert"
                >
                  <AlertTriangle size={14} />
                  <span>Osäkert</span>
                </button>
              </div>

              <div className={`editor-textarea-container ${pasteFeedback ? 'paste-feedback' : ''}`}>
                <textarea
                  ref={textareaRef}
                  className="editor-textarea"
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Skriv anteckningar här..."
                />
                
                {/* Display images inline */}
                {images.length > 0 && (
                  <div className="editor-images">
                    <p className="editor-images-label">Bilder i anteckningen:</p>
                    <div className="editor-images-grid">
                      {images.map(image => (
                        <div key={image.id} className="editor-image-item">
                          {imageUrls[image.id] ? (
                            <img
                              src={imageUrls[image.id]}
                              alt={image.filename}
                              className="editor-image-thumb"
                              onClick={() => setSelectedImage(image)}
                            />
                          ) : (
                            <div className="editor-image-thumb editor-image-loading">
                              Laddar...
                            </div>
                          )}
                          <p className="editor-image-filename">{image.filename}</p>
                        </div>
                      ))}
                    </div>
                    <p className="editor-images-footer">
                      Bilder i anteckningar är privata referenser och bearbetas inte automatiskt.
                    </p>
                  </div>
                )}
              </div>

              <div className="editor-footer">
                <p className="editor-footer-text">
                  Anteckningar är interna arbetsanteckningar och bearbetas inte automatiskt.
                </p>
              </div>
            </>
          ) : (
            <>
              {/* Collapsed preview - shows when no note is active but notes exist */}
              {notes.length > 0 && (
                <div className="editor-collapsed-preview">
                  <div className="collapsed-preview-header">
                    <h4 className="collapsed-preview-title">Anteckningar</h4>
                    <button 
                      className="btn-expand-notes"
                      onClick={() => {
                        // Select the most recently updated note
                        if (notes.length > 0) {
                          setActiveNoteId(notes[0].id)
                        }
                      }}
                      title="Visa anteckningar"
                    >
                      <FileText size={16} />
                    </button>
                  </div>
                  <div className="collapsed-preview-list">
                    {notes.slice(0, 3).map(note => (
                      <div
                        key={note.id}
                        className="collapsed-preview-item"
                        onClick={() => setActiveNoteId(note.id)}
                      >
                        <div className="collapsed-preview-item-title">
                          {note.title || note.preview || '(Tom anteckning)'}
                        </div>
                        <div className="collapsed-preview-item-meta">
                          {formatDate(note.updated_at || note.created_at)}
                        </div>
                      </div>
                    ))}
                    {notes.length > 3 && (
                      <div className="collapsed-preview-more">
                        +{notes.length - 3} fler...
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Empty state - shows when no notes exist */}
              {notes.length === 0 && (
                <div className="editor-empty">
                  <FileText size={48} className="editor-empty-icon" />
                  <p className="editor-empty-text">Välj en anteckning eller skapa en ny</p>
                  <button className="btn-create-note-large" onClick={createNote}>
                    <Plus size={20} />
                    <span>Ny anteckning</span>
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <Modal
          isOpen={!!selectedImage}
          onClose={() => setSelectedImage(null)}
          title="Bild"
        >
          <div className="image-modal-content">
            {imageUrls[selectedImage.id] ? (
              <img 
                src={imageUrls[selectedImage.id]}
                alt={selectedImage.filename}
                className="image-modal-img"
              />
            ) : (
              <div className="image-modal-loading">Laddar bild...</div>
            )}
            <p className="image-modal-filename">{selectedImage.filename}</p>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default JournalistNotes

