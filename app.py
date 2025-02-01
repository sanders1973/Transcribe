from shiny import App, reactive, render, ui
import json

app_ui = ui.page_fluid(
    ui.card(
        ui.card_header("Audio Recorder"),
        ui.input_action_button("record", "Start Recording", class_="btn-primary"),
        ui.input_action_button("stop", "Stop Recording", class_="btn-danger"),
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
        )
    )
)

def server(input, output, session):
    # JavaScript code for audio recording
    session.browser.run_script("""
    let mediaRecorder;
    let audioChunks = [];
    
    async function startRecording() {
        audioChunks = [];
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            document.getElementById('audio-player').src = audioUrl;
        };
        
        mediaRecorder.start();
        document.getElementById('recording-status').textContent = 'Recording...';
    }
    
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            document.getElementById('recording-status').textContent = '';
        }
    }
    
    Shiny.setInputValue('recorder_ready', true);
    """)
    
    @reactive.effect
    @reactive.event(input.record)
    def _():
        session.browser.run_script("startRecording()")
    
    @reactive.effect
    @reactive.event(input.stop)
    def _():
        session.browser.run_script("stopRecording()")

app = App(app_ui, server)
