---
name: Browser-inspelning för Röstmemo
overview: "Implementera MediaRecorder-baserad direktinspelning i ProjectDetail när ingestMode === 'audio', med två lägen: \"Spela in\" och \"Ladda upp fil\". Backend accepterar redan webm/ogg via befintlig endpoint."
todos:
  - id: add-recording-state
    content: Lägg till MediaRecorder state-variabler (isRecording, recordingTime, mediaRecorder, audioChunks, recordingMode, micPermissionError)
    status: completed
  - id: add-recording-functions
    content: Implementera startRecording(), stopRecording(), uploadRecordingBlob(), formatTime() funktioner
    status: completed
    dependencies:
      - add-recording-state
  - id: update-audio-ui
    content: "Ersätt dropzone-sektion när ingestMode === 'audio' med två lägen: 'Spela in' och 'Ladda upp fil'"
    status: completed
    dependencies:
      - add-recording-functions
  - id: add-recording-css
    content: Lägg till CSS-styling för recording-kontroller (mode selector, start/stop buttons, timer, indicators)
    status: completed
    dependencies:
      - update-audio-ui
  - id: remove-debug-logs
    content: Ta bort debug-logs från tidigare felsökning (rad 349-354, 477-478)
    status: completed
    dependencies:
      - update-audio-ui
  - id: verify-implementation
    content: "Kör manual verification checklist: start/stop blob, upload, dokument skapas, event metadata, fail-closed"
    status: in_progress
    dependencies:
      - add-recording-css
      - remove-debug-logs
---

# Plan:

Browser-inspelning för Röstmemo

## Översikt

Lägg till MediaRecorder-baserad direktinspelning i [apps/web/src/pages/ProjectDetail.jsx](apps/web/src/pages/ProjectDetail.jsx) när `ingestMode === 'audio'`. Backend kräver inga ändringar - befintlig endpoint `/api/projects/{project_id}/recordings` accepterar redan multipart file och hanterar webm/ogg.

## Arkitektur

```mermaid
flowchart TD
    A[User clicks Röstmemo] --> B{ingestMode === 'audio'}
    B --> C[Show two modes]
    C --> D[Spela in button]
    C --> E[Ladda upp fil button]
    D --> F[Request mic permission]
    F --> G{Permission granted?}
    G -->|No| H[Show error + fallback to file upload]
    G -->|Yes| I[Start MediaRecorder]
    I --> J[Show timer mm:ss]
    J --> K[User clicks Stop]
    K --> L[Create blob from recording]
    L --> M[Upload to /api/projects/{id}/recordings]
    M --> N[Processing state 800-1200ms]
    N --> O[Show success + link to document]
    E --> P[Existing file input flow]
```

## Backend (ingen ändring)

Befintlig endpoint i [apps/api/main.py](apps/api/main.py) (rad 501-687) accepterar redan:

- Multipart file upload
- Alla MIME-typer (använder `file.content_type` eller fallback)
- Webm/ogg fungerar automatiskt (hanteras som generisk file)

**Verifiering:** Endpoint accepterar redan webm/ogg utan ändringar.

## Frontend-ändringar

### 1. Nya state-variabler

I [apps/web/src/pages/ProjectDetail.jsx](apps/web/src/pages/ProjectDetail.jsx), lägg till efter rad 34:

```javascript
// MediaRecorder states
const [isRecording, setIsRecording] = useState(false)
const [recordingTime, setRecordingTime] = useState(0) // seconds
const [mediaRecorder, setMediaRecorder] = useState(null)
const [audioChunks, setAudioChunks] = useState([])
const [recordingMode, setRecordingMode] = useState('upload') // 'upload' | 'record'
const [micPermissionError, setMicPermissionError] = useState(null)
```

### 2. MediaRecorder-funktioner

Lägg till efter `handleAudioSelect` (efter rad 153):

**KRITISKT:** Använd samma auth-mönster som övriga API-anrop i projektet (se rad 38-40, 108-110). Projektet använder `const username = 'admin'; const password = 'password'; const auth = btoa(...)` - följ samma mönster för konsistens.

```javascript
const startRecording = async () => {
  let stream = null
  let timer = null
  
  try {
    setMicPermissionError(null)
    
    // Check MediaRecorder support
    if (!window.MediaRecorder || !navigator.mediaDevices) {
      throw new Error('MediaRecorder stöds inte i denna webbläsare')
    }
    
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    
    // Determine MIME type (prefer webm, fallback to ogg, fail if neither)
    let mimeType = null
    if (MediaRecorder.isTypeSupported('audio/webm')) {
      mimeType = 'audio/webm'
    } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
      mimeType = 'audio/ogg'
    } else {
      stream.getTracks().forEach(track => track.stop())
      throw new Error('Inget ljudformat stöds. Använd fil-uppladdning istället.')
    }
    
    const recorder = new MediaRecorder(stream, { mimeType })
    const chunks = []
    
    // Single onstop handler (no duplication)
    recorder.onstop = async () => {
      if (timer) clearInterval(timer)
      
      try {
        const blob = new Blob(chunks, { type: mimeType })
        await uploadRecordingBlob(blob)
      } finally {
        // Always stop stream tracks
        if (stream) {
          stream.getTracks().forEach(track => track.stop())
        }
      }
    }
    
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    
    recorder.start()
    setMediaRecorder(recorder)
    setAudioChunks(chunks)
    setIsRecording(true)
    setRecordingTime(0)
    
    // Timer with cleanup
    timer = setInterval(() => {
      setRecordingTime(prev => {
        const newTime = prev + 1
        // Auto-stop at 30 seconds (UI limit for demo)
        if (newTime >= 30) {
          stopRecording()
        }
        return newTime
      })
    }, 1000)
    
  } catch (err) {
    // Cleanup on error
    if (timer) clearInterval(timer)
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
    }
    
    setMicPermissionError(`Mikrofonåtkomst nekad eller stöds inte: ${err.message}`)
    // Don't auto-switch - user must click "Byt till uppladdning"
  }
}

const stopRecording = () => {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop()
    setIsRecording(false)
    // Timer cleanup handled in onstop
  }
}

const uploadRecordingBlob = async (blob) => {
  setRecordingUploading(true)
  setRecordingProcessing(false)
  setRecordingError(null)
  setRecordingSuccess(null)
  
  try {
    // Use same auth pattern as other API calls in project (see fetchProject, handleAudioSelect)
    const username = 'admin'
    const password = 'password'
    const auth = btoa(`${username}:${password}`)
    
    // Convert Blob to File for FormData
    const filename = `recording_${Date.now()}.${blob.type.includes('webm') ? 'webm' : 'ogg'}`
    const file = new File([blob], filename, { type: blob.type })
    
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`http://localhost:8000/api/projects/${id}/recordings`, {
      method: 'POST',
      headers: { 'Authorization': `Basic ${auth}` },
      body: formData
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Kunde inte ladda upp inspelning')
    }
    
    const documentData = await response.json()
    
    setRecordingUploading(false)
    setRecordingProcessing(true)
    
    // Processing delay: 800-1200ms (same as handleAudioSelect)
    const delay = 800 + Math.random() * 400
    await new Promise(resolve => setTimeout(resolve, delay))
    
    setRecordingProcessing(false)
    setRecordingSuccess({ documentId: documentData.id })
    await fetchProject()
  } catch (err) {
    setRecordingUploading(false)
    setRecordingProcessing(false)
    setRecordingError(err.message)
  }
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}
```

### 3. UI-ändringar för audio-läge

Ersätt dropzone-sektionen (rad 448-495) när `ingestMode === 'audio'`:

```javascript
{ingestMode === 'audio' ? (
  <div className="audio-recording-container">
    {/* Mode selector */}
    <div className="recording-mode-selector">
      <button
        className={`mode-btn ${recordingMode === 'record' ? 'active' : ''}`}
        onClick={() => {
          setRecordingMode('record')
          setMicPermissionError(null)
        }}
        disabled={isRecording || recordingUploading || recordingProcessing}
      >
        <Mic size={16} />
        <span>Spela in</span>
      </button>
      <button
        className={`mode-btn ${recordingMode === 'upload' ? 'active' : ''}`}
        onClick={() => {
          setRecordingMode('upload')
          setMicPermissionError(null)
        }}
        disabled={isRecording || recordingUploading || recordingProcessing}
      >
        <Upload size={16} />
        <span>Ladda upp fil</span>
      </button>
    </div>
    
    {/* Recording mode */}
    {recordingMode === 'record' ? (
      <div className="recording-controls">
        {micPermissionError && (
          <div className="recording-error">{micPermissionError}</div>
        )}
        {!isRecording && !recordingUploading && !recordingProcessing && (
          <button
            className="record-start-btn"
            onClick={startRecording}
            disabled={!navigator.mediaDevices || !window.MediaRecorder}
          >
            <Mic size={24} />
            <span>Starta inspelning</span>
          </button>
        )}
        {isRecording && (
          <div className="recording-active">
            <div className="recording-indicator">
              <div className="recording-dot"></div>
              <span>Inspelar: {formatTime(recordingTime)}</span>
              {recordingTime >= 30 && <span className="recording-limit"> (Max 30 sek)</span>}
            </div>
            <button className="record-stop-btn" onClick={stopRecording}>
              Stoppa
            </button>
          </div>
        )}
        {(recordingUploading || recordingProcessing) && (
          <div className="recording-status">
            {recordingUploading ? 'Laddar upp...' : 'Bearbetar...'}
          </div>
        )}
      </div>
    ) : (
      /* Upload mode - existing file input */
      <div 
        className={`ingest-dropzone ${recordingUploading || recordingProcessing ? 'uploading' : ''}`}
        onClick={() => audioInputRef.current?.click()}
      >
        <input
          ref={audioInputRef}
          type="file"
          accept="audio/*"
          onChange={handleAudioSelect}
          style={{ display: 'none' }}
        />
        <div className="dropzone-content">
          <Upload size={32} className="dropzone-icon" />
          <p className="dropzone-text">Dra hit en ljudfil eller klicka för att välja</p>
          <p className="dropzone-hint">Ljudfiler • Max 25MB</p>
        </div>
      </div>
    )}
    
    {/* Success message */}
    {recordingSuccess && (
      <div className="recording-success">
        <p>Inspelning sparad!</p>
        <Link to={`/documents/${recordingSuccess.documentId}`}>
          Öppna dokument
        </Link>
      </div>
    )}
    
    {/* Error message */}
    {recordingError && (
      <div className="recording-error">{recordingError}</div>
    )}
  </div>
) : (
  /* Existing document dropzone */
  ...
)}
```

### 4. CSS-styling

Lägg till i [apps/web/src/pages/ProjectDetail.css](apps/web/src/pages/ProjectDetail.css):

```css
.audio-recording-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.recording-mode-selector {
  display: flex;
  gap: 0.5rem;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid var(--color-border-default);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.15s;
}

.mode-btn.active {
  background: var(--color-bg-active);
  border-color: var(--color-brand-red);
  color: var(--color-text-primary);
}

.recording-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: 0.5rem;
  box-shadow: var(--shadow-sm);
}

.record-start-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 2rem;
  background: var(--color-brand-red);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
}

.recording-active {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.recording-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

.recording-limit {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.recording-dot {
  width: 12px;
  height: 12px;
  background: var(--color-brand-red);
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.record-stop-btn {
  padding: 0.75rem 1.5rem;
  background: var(--color-accent-error);
  color: var(--color-interactive-text);
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  font-family: var(--font-sans);
  transition: all 0.15s;
}

.record-stop-btn:hover {
  opacity: 0.9;
}

.recording-error {
  padding: 1rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-accent-error);
  border-radius: 0.5rem;
  color: var(--color-accent-error);
  text-align: center;
}

.recording-fallback-btn {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid var(--color-border-default);
  border-radius: 0.25rem;
  color: var(--color-text-primary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: var(--font-size-base);
  transition: all 0.15s;
}

.recording-fallback-btn:hover {
  background: var(--color-bg-active);
  border-color: var(--color-border-hover);
}
```

## Verifiering

### Manual checklist

Lägg till i `docs/runbook.md` eller befintlig verifieringsdoc:

**a) Start/Stop skapar blob och upload (Network):**

- Klicka "Spela in" → "Starta inspelning"
- Verifiera att timer startar (mm:ss)
- Klicka "Stoppa" (eller vänta till auto-stop vid 30 sek)
- Verifiera i Network tab att blob skapas och POST till `/api/projects/{id}/recordings` skickas
- Verifiera att webm/ogg blob skickas med korrekt MIME-type i request

**b) Dokument skapas och öppnas:**

- Verifiera att dokument visas i Material-listan med korrekt filnamn
- Klicka på dokumentet och verifiera att DocumentView öppnas
- Verifiera att maskerad text visas korrekt

**c) Event metadata:**

- Verifiera `recording_transcribed` event i API (GET `/api/projects/{id}/events`)
- Kontrollera att event_metadata innehåller: `mime`, `size`, `recording_file_id`
- Kontrollera att `duration` finns om tillgänglig
- **KRITISKT:** Verifiera att INGET raw transcript, textutdrag eller filnamn finns i event

**d) Permission denied ger fail-closed + möjlighet till uppladdning:**

- Neka mikrofon-permission i browser (eller använd browser som saknar MediaRecorder)
- Verifiera att tydligt fel visas med meddelande
- Verifiera att knapp "Byt till uppladdning" visas
- Klicka på knappen och verifiera att fil-uppladdning fungerar
- **KRITISKT:** Ingen silent auto-switch ska ske

### Smoke test (valfritt)

Lägg till i Makefile:

```makefile
verify-recording:
	@echo "Manual verification required:"
	@echo "1. Start recording in browser"
	@echo "2. Stop after 5 seconds"
	@echo "3. Verify document created"
	@echo "4. Check event metadata"
```

## Filer att ändra

1. [apps/web/src/pages/ProjectDetail.jsx](apps/web/src/pages/ProjectDetail.jsx)

- Lägg till MediaRecorder state-variabler (isRecording, recordingTime, mediaRecorder, audioChunks, recordingMode, micPermissionError)
- Lägg till `startRecording`, `stopRecording`, `uploadRecordingBlob`, `formatTime` funktioner
- **KRITISKT:** En (1) onstop-handler, timer cleanup, stream tracks cleanup i finally
- **KRITISKT:** Max 30 sek auto-stop i UI (inte backend)
- **KRITISKT:** Fail-closed vid permission error med knapp "Byt till uppladdning" (ingen auto-switch)
- Ersätt dropzone-sektion när `ingestMode === 'audio'` med mode selector + två lägen
- Ta bort ALLA debug-logs relaterade till audio/recording (rad 349-354, 477-478, och eventuella andra)

2. [apps/web/src/pages/ProjectDetail.css](apps/web/src/pages/ProjectDetail.css)

- Lägg till CSS för recording-kontroller

## Risker

- **MediaRecorder support:** Alla moderna browsers stödjer, men fallback till file upload hanteras
- **Permission errors:** Fail-closed med tydligt fel + fallback
- **Blob size:** MediaRecorder kan skapa stora blobs vid långa inspelningar - 25MB-gränsen gäller

## Efter implementation

1. **Restart frontend:** `docker-compose restart web` (backend behöver inte restartas)
2. **Kör manual verification checklist** (a-d ovan)
3. **Rapportera resultat:**

   - Filer ändrade
   - Verifiering resultat (a-d)
   - Bekräftelse att debug-logs är borttagna
   - Bekräftelse att CSS använder tokens (inga hardkodade färger)