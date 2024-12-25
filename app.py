from flask import Flask, render_template, request, send_file
import qrcode
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # You can set a random secret key

@app.route("/", methods=["GET", "POST"])
def generate_qr():
    if request.method == "POST":
        data = request.form['text']
        qr = qrcode.make(data)

        # Save the QR code to a BytesIO object
        img_io = BytesIO()
        qr.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png', as_attachment=True, download_name="qr_code.png")

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
