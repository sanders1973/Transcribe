from shiny import App, reactive, render, ui
import google.generativeai as genai
import base64
import io

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_text("gemini_key", "Gemini API Key", password=True),
        ui.hr(),
        ui.input_action_button("record", "Start Recording", class_="btn-primary"),
        ui.input_action_button("stop", "Stop Recording", class_="btn-danger"),
        ui.input_action_button("transcribe", "Transcribe Audio", class_="btn-success"),
    ),
    ui.card(
        ui.card_header("Audio Recorder"),
        ui.tags.div(
            ui.tags.audio(
                id="audio-player",
                controls=True,
                style="margin-top: 10px;"
            )
        ),
        ui.tags.div(
            id="recording-status",
            style="margin-top: 10px; color: red;"
        ),
        ui.output_text_verbatim("transcription")
    ),
    ui.head_content(
        ui.tags.script("""
            // Initialize Shiny message handlers
            window.Shiny = window.Shiny || {};
            window.Shiny._handlers = window.Shiny._handlers || {};
            window.Shiny.addCustomMessageHandler = function(type, handler) {
                window.Shiny._handlers[type] = handler;
            };
            
            // Global variables
            let mediaRecorder = null;
            let audioChunks = [];
            let audioBlob = null;
            
            // Define the recording functions
            async function startRecording() {
                console.log('Attempting to start recording');
                document.getElementById('recording-status').textContent = 'Requesting microphone access...';
                
                audioChunks = [];
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    
                    mediaRecorder.addEventListener('dataavailable', (event) => {
                        audioChunks.push(event.data);
                    });
                    
                    mediaRecorder.addEventListener('stop', () => {
                        audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const audioUrl = URL.createObjectURL(audioBlob);
                        document.getElementById('audio-player').src = audioUrl;
                        document.getElementById('recording-status').textContent = 'Recording complete';
                    });
                    
                    mediaRecorder.start();
                    document.getElementById('recording-status').textContent = 'Recording...';
                    console.log('Recording started');
                    
                } catch (err) {
                    console.error('Error:', err);
                    document.getElementById('recording-status').textContent = 
                        'Error: ' + (err.message || 'Could not access microphone');
                }
            }
            
            function stopRecording() {
                console.log('Stopping recording');
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                }
            }

            async function sendAudioToServer() {
                if (!audioBlob) {
                    document.getElementById('recording-status').textContent = 'No recording available';
                    return;
                }
                
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = function() {
                    const base64Audio = reader.result.split(',')[1];
                    Shiny.setInputValue('audio_data', base64Audio);
                }
            }
            
            // Add click handlers directly to buttons
            document.addEventListener('DOMContentLoaded', () => {
                console.log('Setting up button handlers');
                document.getElementById('record').addEventListener('click', startRecording);
                document.getElementById('stop').addEventListener('click', stopRecording);
                document.getElementById('transcribe').addEventListener('click', sendAudioToServer);
            });
        """)
    )
)

def server(input, output, session):
    transcript = reactive.value("")
    
    @reactive.effect
    @reactive.event(input.record)
    def _():
        session.send_custom_message("startRecording", "start")
    
    @reactive.effect
    @reactive.event(input.stop)
    def _():
        session.send_custom_message("stopRecording", "stop")
        
    @reactive.effect
    @reactive.event(input.audio_data)
    async def _():
        try:
            # Configure Gemini
            genai.configure(api_key=input.gemini_key())
            
            # Get the base64 audio data
            audio_data = base64.b64decode(input.audio_data())
            
            # Create a model instance
            model = genai.GenerativeModel('gemini-pro')
            
            # Send audio for transcription
            response = await model.generate_content(audio_data)
            
            # Update the transcript
            transcript.set(response.text)
            
        except Exception as e:
            transcript.set(f"Error during transcription: {str(e)}")

    @output
    @render.text
    def transcription():
        return transcript()

app = App(app_ui, server)
