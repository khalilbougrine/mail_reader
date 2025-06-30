import imaplib
import email
import os
import requests
import json
import mysql.connector
from mysql.connector import Error
from pdf2image import convert_from_path
import tempfile
import shutil

# --- Configuration email ---
EMAIL = "testtt999testtt@gmail.com"
PASSWORD = "nfbykrznbanluhor"
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

# --- Configuration MySQL ---
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'candidatures_db'
}

# --- Dossier local ---
SAVE_DIR = "cv_inbox"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- Extensions supportées ---
VALID_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg']
VALID_CONVERTIBLE_EXTENSIONS = ['.pdf']  # tu peux ajouter '.docx' ici plus tard

# --- Convertir PDF en image ---
def convertir_en_image_si_necessaire(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext in VALID_IMAGE_EXTENSIONS:
        return filepath  # déjà image

    if ext == '.pdf':
        print("🔄 Conversion PDF → image")
        try:
            images = convert_from_path(filepath)
            if images:
                image_path = filepath.replace(ext, "_page1.jpg")
                images[0].save(image_path, "JPEG")
                print(f"📷 Image générée : {image_path}")
                return image_path
        except Exception as e:
            print(f"❌ Erreur conversion PDF : {e}")
            return None

    print(f"⛔ Format non supporté pour conversion : {filepath}")
    return None

# --- Insertion directe en base ---
def insert_into_db(data):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
            INSERT INTO fiche_candidat (
                name, email, phone, address, birthdate, linkedin, github,
                resume_title, profil, skills, education, experience,
                projects, certifications, languages, interests, image, created_at
            ) VALUES (
                %(name)s, %(email)s, %(phone)s, %(address)s, %(birthdate)s, %(linkedin)s, %(github)s,
                %(resume_title)s, %(profil)s, %(skills)s, %(education)s, %(experience)s,
                %(projects)s, %(certifications)s, %(languages)s, %(interests)s, %(image)s, NOW()
            )
        """

        cursor.execute(insert_query, {
            'name': data.get('name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'address': data.get('address'),
            'birthdate': data.get('birthdate') if data.get('birthdate') else None,
            'linkedin': data.get('linkedin'),
            'github': data.get('github'),
            'resume_title': data.get('resume_title'),
            'profil': data.get('profil'),
            'skills': json.dumps(data.get('skills')),
            'education': json.dumps(data.get('education')),
            'experience': json.dumps(data.get('experience')),
            'projects': json.dumps(data.get('projects')),
            'certifications': json.dumps(data.get('certifications')),
            'languages': json.dumps(data.get('languages')),
            'interests': json.dumps(data.get('interests')),
            'image': data.get('image')
        })


        connection.commit()
        print(f"🟢 Insertion MySQL réussie pour : {data.get('email')}")

    except Error as e:
        print(f"❌ Erreur MySQL : {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# --- Connexion mail ---
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(EMAIL, PASSWORD)
mail.select("inbox")

# --- Mails non lus ---
status, messages = mail.search(None, '(UNSEEN)')
if status != "OK":
    print("Erreur de recherche.")
    exit()

for num in messages[0].split():
    status, data = mail.fetch(num, "(RFC822)")
    if status != "OK":
        continue

    email_msg = email.message_from_bytes(data[0][1])
    subject = email_msg["subject"]
    print(f"📩 Nouveau mail : {subject}")

    for part in email_msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            if not filename:
                continue

            ext = os.path.splitext(filename)[1].lower()
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(part.get_payload(decode=True))
            print(f"✅ Fichier sauvegardé : {filename}")

            # 🔄 Conversion si nécessaire
            image_path = convertir_en_image_si_necessaire(filepath)
            if not image_path:
                continue  # on ignore le fichier s'il n'est pas convertible

            try:
                with open(image_path, 'rb') as file:
                    files = {'file': file}
                    response = requests.post('http://69.62.106.98:6600/cv', files=files)

                    if response.status_code == 200:
                        result = response.json()
                        print(f"🎯 Résultat IA reçu pour {filename}")

                        # Facultatif : debug JSON
                        json_name = os.path.splitext(filename)[0] + "_parsed.json"
                        with open(os.path.join(SAVE_DIR, json_name), 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=4)

                        # 🔁 Enregistrement en base
                        insert_into_db(result)

                    else:
                        print(f"❌ Erreur FastAPI : {response.status_code}")
                        print(response.text)

            except Exception as e:
                print(f"⚠️ Exception IA : {e}")

mail.logout()
