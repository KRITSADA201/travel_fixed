# Travel Recommend — ระบบแนะนำสถานที่ท่องเที่ยว

## วิธีติดตั้ง

1. ติดตั้ง dependencies
```bash
pip install -r requirements.txt
```

2. คัดลอกไฟล์ `.env.example` แล้วเปลี่ยนชื่อเป็น `.env` และใส่ค่าจริง
```bash
cp .env.example .env
```

3. รันแอป
```bash
python app.py
```

เปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:5000`

## บัญชี Admin เริ่มต้น
- Username: `admin`
- Password: `admin123`

## ฟีเจอร์
- แสดงสถานที่ท่องเที่ยวแยกตามหมวดหมู่
- ระบบค้นหา
- ระบบรีวิวและให้คะแนน (กดดาว)
- ระบบบันทึกรายการโปรด
- แผนที่และนำทาง
- Login ด้วย Google / LINE / Facebook
- Admin จัดการสถานที่และหมวดหมู่
