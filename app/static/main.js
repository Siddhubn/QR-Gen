// QRglyph main.js
// Handles TTS, share, and dynamic UI

function readQRContent(text) {
    if (!('speechSynthesis' in window)) {
        alert('Text-to-speech not supported on this device.');
        return;
    }
    if (!text || text === 'None') {
        alert('No QR content to read aloud.');
        return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.0;
    utter.pitch = 1.0;
    utter.lang = 'en-US';
    window.speechSynthesis.speak(utter);
}

function shareQR(qrImageB64, content) {
    const shareData = {
        title: 'QRglyph QR Code',
        text: content,
        url: window.location.href
    };
    if (navigator.share) {
        navigator.share(shareData).catch(() => {
            alert('Share cancelled or failed.');
        });
    } else {
        alert('Web Share API not supported. You can copy the content manually.');
    }
}
