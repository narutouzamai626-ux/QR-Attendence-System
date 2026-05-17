import qrcode

data = "QR Attendance System"

qr = qrcode.make(data)

qr.save("attendance_qr.png")

print("QR Code Generated Successfully")