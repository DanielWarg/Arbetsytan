import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'
import './Intro.css'

const LS_KEY = 'arbetsytan_skip_intro_v1'

function getSkipIntro() {
  try {
    return localStorage.getItem(LS_KEY) === '1'
  } catch {
    return false
  }
}

function setSkipIntro(value) {
  try {
    localStorage.setItem(LS_KEY, value ? '1' : '0')
  } catch {
    // ignore
  }
}

export default function Intro() {
  const navigate = useNavigate()
  const forceIntro = useMemo(() => {
    try {
      return new URLSearchParams(window.location.search).get('intro') === '1'
    } catch {
      return false
    }
  }, [])

  const [skipNext, setSkipNext] = useState(getSkipIntro())

  const videoSrc = useMemo(() => {
    // Place a file in apps/web/public/showreel.mp4 or set VITE_SHOWREEL_VIDEO_URL
    return import.meta.env.VITE_SHOWREEL_VIDEO_URL || '/showreel.mp4'
  }, [])

  useEffect(() => {
    // If user opted out, go straight to the UI
    if (!forceIntro && getSkipIntro()) {
      navigate('/projects', { replace: true })
    }
  }, [navigate, forceIntro])

  const goToDemo = () => {
    setSkipIntro(skipNext)
    navigate('/projects', { replace: true })
  }

  return (
    <div className="intro-page">
      <div className="intro-card">
        <div className="intro-header">
          <div className="intro-kicker">Showreel</div>
          <h1 className="intro-title">Arbetsytan</h1>
          <p className="intro-subtitle">
            Säker journalistisk arbetsyta med Scout och Fort Knox (lokal LLM).
          </p>
        </div>

        <div className="intro-video-shell">
          {/* Placeholder-friendly: video will show controls even if file is missing */}
          <video
            className="intro-video"
            src={videoSrc}
            controls
            playsInline
            preload="metadata"
          />
          <div className="intro-video-hint">
            Lägg din video i <code>apps/web/public/showreel.mp4</code> eller sätt{' '}
            <code>VITE_SHOWREEL_VIDEO_URL</code>.
          </div>
        </div>

        <div className="intro-actions">
          <Button onClick={goToDemo}>Gå till demo</Button>
          <label className="intro-checkbox">
            <input
              type="checkbox"
              checked={skipNext}
              onChange={(e) => setSkipNext(e.target.checked)}
            />
            Hoppa över intro nästa gång
          </label>
        </div>
      </div>
    </div>
  )
}

