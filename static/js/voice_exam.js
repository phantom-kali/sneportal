// Voice Exam System JavaScript

class VoiceExamSystem {
    constructor() {
        this.initializeVariables();
        this.bindElements();
        this.setupEventListeners();
    }

    initializeVariables() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.sessionData = null;
        this.updateTimer = null;
        this.ttsQueue = [];
        this.isPlaying = false;
        this.silenceTimeout = null;
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.silenceStart = null;
        this.SILENCE_THRESHOLD = -50; // dB
        this.MAX_SILENCE_DURATION = 2000; // 2 seconds of silence before stopping
    }

    bindElements() {
        this.setupPanel = document.getElementById('setupPanel');
        this.voiceInterface = document.getElementById('voiceInterface');
        this.examSelect = document.getElementById('examSelect');
        this.startExamButton = document.getElementById('startExamButton');
        this.recordButton = document.getElementById('recordButton');
        this.repeatButton = document.getElementById('repeatButton');
        this.stopExamButton = document.getElementById('stopExamButton');
        this.sessionState = document.getElementById('sessionState');
        this.timeRemaining = document.getElementById('timeRemaining');
        this.progressBar = document.getElementById('progressBar');
        this.questionNumber = document.getElementById('questionNumber');
        this.questionText = document.getElementById('questionText');
    }

    setupEventListeners() {
        // Exam selection change
        this.examSelect.addEventListener('change', () => {
            this.startExamButton.disabled = !this.examSelect.value;
        });

        // Form submission
        document.getElementById('examSetupForm').addEventListener('submit', (e) => this.handleExamStart(e));

        // Voice control buttons
        this.recordButton.addEventListener('click', () => this.toggleRecording());
        this.repeatButton.addEventListener('click', () => this.repeatQuestion());
        this.stopExamButton.addEventListener('click', () => this.handleStopExam());
    }

    async handleExamStart(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        try {
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: formData
            });
            
            const data = await response.json();
            if (data.success) {
                this.sessionData = data;
                this.setupPanel.classList.add('hidden');
                this.voiceInterface.classList.add('active');
                this.startExamSession();
                // Immediately start voice introduction
                this.playWelcomeMessage();
            } else {
                this.showFeedback(data.error || 'Failed to start exam', 'error');
            }
        } catch (error) {
            this.showFeedback('Failed to start exam session', 'error');
        }
    }

    async playWelcomeMessage() {
        const welcomeText = `Welcome to the voice exam system. I will be your voice assistant throughout this exam. 
                           First, please state your full name after the tone.`;
        await this.playTTSResponse(welcomeText);
        await this.playTone();
        this.startRecording(); // Automatically start recording for name input
    }

    getMessagesContainer() {
        let messages = document.getElementById('messages');
        if (!messages) {
            messages = document.createElement('div');
            messages.id = 'messages';
            messages.className = 'messages';
            document.querySelector('.container').insertBefore(messages, this.setupPanel);
        }
        return messages;
    }

    showFeedback(message, type = 'success') {
        const feedback = document.createElement('div');
        feedback.className = `feedback ${type}`;
        feedback.textContent = message;
        
        const messages = this.getMessagesContainer();
        messages.appendChild(feedback);
        
        // Also play the feedback message for blind students
        this.playTTSResponse(message);
        
        setTimeout(() => {
            if (feedback.parentNode) {
                feedback.remove();
            }
        }, 5000);
    }

    async initializeRecording() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.mediaStream);

            // Initialize Web Audio API components for voice detection
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            source.connect(this.analyser);
            
            // Configure analyser
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.8;

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                // Play end tone before processing
                await this.playEndTone();
                await this.processAudioResponse(audioBlob);
                this.audioChunks = [];
            };
        } catch (error) {
            this.showFeedback('Microphone access denied. Please enable microphone access.', 'error');
        }
    }

    detectSilence() {
        if (!this.isRecording) return;

        const dataArray = new Float32Array(this.analyser.frequencyBinCount);
        this.analyser.getFloatFrequencyData(dataArray);

        // Calculate average volume level
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;

        if (average < this.SILENCE_THRESHOLD) {
            if (!this.silenceStart) {
                this.silenceStart = Date.now();
            } else if (Date.now() - this.silenceStart >= this.MAX_SILENCE_DURATION) {
                this.stopRecording();
                return;
            }
        } else {
            this.silenceStart = null;
        }

        // Continue monitoring while recording
        if (this.isRecording) {
            requestAnimationFrame(() => this.detectSilence());
        }
    }

    async playEndTone() {
        // Play a different tone to indicate recording end
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(context.destination);

        oscillator.frequency.setValueAtTime(600, context.currentTime); // Different frequency from start tone
        gainNode.gain.setValueAtTime(0.5, context.currentTime);

        oscillator.start();
        gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.5);
        
        return new Promise(resolve => {
            setTimeout(() => {
                oscillator.stop();
                resolve();
            }, 500);
        });
    }

    async processAudioResponse(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob);
        if (this.sessionData?.session_id) {
            formData.append('session_id', this.sessionData.session_id);
        }

        try {
            const response = await fetch('/voice/process/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            await this.handleVoiceResponse(data);
        } catch (error) {
            this.showFeedback('Failed to process voice input', 'error');
        }
    }

    async handleVoiceResponse(data) {
        if (data.error) {
            await this.playTTSResponse(data.message || data.error);
            if (data.state === 'exam_complete') {
                this.endExam();
            }
            return;
        }

        // Play the response and automatically start recording after it's done
        if (data.text) {
            await this.playTTSResponse(data.text);
            if (data.include_tone) {
                await this.playTone();
                this.startRecording();
            }
        }

        this.updateSessionState(data);
    }

    async playTTSResponse(text) {
        try {
            const response = await fetch('/voice/tts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: `text=${encodeURIComponent(text)}`
            });

            if (response.ok) {
                const blob = await response.blob();
                const audio = new Audio(URL.createObjectURL(blob));
                
                return new Promise((resolve) => {
                    audio.onended = resolve;
                    audio.play();
                });
            }
        } catch (error) {
            console.error('TTS playback failed:', error);
        }
    }

    async updateSessionState(data = null) {
        if (!data) {
            try {
                const response = await fetch(`/session/state/?session_id=${this.sessionData?.session_id}`);
                data = await response.json();
            } catch (error) {
                console.error('Failed to update session state:', error);
                return;
            }
        }

        if (data.state === 'exam_complete') {
            this.endExam();
            return;
        }

        // Update UI elements
        this.sessionState.textContent = this.formatState(data.state);
        this.timeRemaining.textContent = data.time_remaining_formatted;
        this.progressBar.style.width = `${data.progress_percentage}%`;

        if (data.current_question) {
            this.questionNumber.textContent = `Question ${data.current_question_index + 1} of ${data.total_questions}`;
            this.questionText.textContent = data.current_question.text;
        }
    }

    formatState(state) {
        return state.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    async startExamSession() {
        await this.initializeRecording();
        await this.updateSessionState();
        this.updateTimer = setInterval(() => this.updateSessionState(), 1000);
    }

    endExam() {
        clearInterval(this.updateTimer);
        window.location.href = `/results/${this.sessionData?.session_id}/`;
    }

    startRecording() {
        if (this.mediaRecorder && !this.isRecording) {
            this.mediaRecorder.start();
            this.isRecording = true;
            this.silenceStart = null;
            this.recordButton.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
            this.recordButton.classList.add('recording');
            // Start silence detection
            this.detectSilence();
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.recordButton.innerHTML = '<i class="fas fa-microphone"></i> Start Speaking';
            this.recordButton.classList.remove('recording');
        }
    }

    toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.playTone().then(() => this.startRecording());
        }
    }

    async playTone() {
        try {
            const response = await fetch('/voice/tone/');
            if (response.ok) {
                const blob = await response.blob();
                const audio = new Audio(URL.createObjectURL(blob));
                return new Promise((resolve) => {
                    audio.onended = resolve;
                    audio.play();
                });
            }
        } catch (error) {
            console.error('Failed to play tone:', error);
        }
    }

    async repeatQuestion() {
        if (this.sessionData?.current_question) {
            await this.playTTSResponse(this.sessionData.current_question.text);
        }
    }

    async handleStopExam() {
        const confirmText = 'Are you sure you want to stop the exam? Say yes or no.';
        await this.playTTSResponse(confirmText);
        await this.playTone();
        this.startRecording();
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize the voice exam system when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.voiceExam = new VoiceExamSystem();
});
