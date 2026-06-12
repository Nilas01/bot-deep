import os
import logging
import nest_asyncio
import asyncio
import random
import io
import json
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# Configuration Render
nest_asyncio.apply()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION DU TOKEN ---
TOKEN = "8402606079:AAE74zmoeXlBehpOOsRAa2O3OkyM0ze1wSA"

# Base de données Quiz
QUIZ_DATA = [
    {"q": "Quelle est la capitale de la France ?", "o": ["A) Lyon", "B) Marseille", "C) Paris", "D) Toulouse"], "r": "C"},
    {"q": "Quel organe permet de pomper le sang dans le corps ?", "o": ["A) Le foie", "B) Le cœur", "C) Le poumon", "D) Le cerveau"], "r": "B"},
    {"q": "En quelle année l'homme a-t-il marché sur la Lune ?", "o": ["A) 1962", "B) 1969", "C) 1975", "D) 1980"], "r": "B"}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['search_active'] = False
    texte = (
        "🤖 Bienvenue sur DEEP 2.0 (Version Vocale OK) !\n\n"
        "Voici mes fonctionnalités :\n"
        "• 🔍 *Question/IA* : Appuie sur /search pour m'activer en continu.\n"
        "• 🎙️ *Recherche Vocale* : Active /search, puis envoie-moi une note vocale ! Je vais chercher pour toi.\n"
        "• 🎨 *Générer une image* : Écris 'imagine' suivi de ton idée (Ex: imagine un lion bleu).\n"
        "• 🎮 *Quiz* : Appuie sur /quiz pour jouer !"
    )
    clavier = [['/search', '/quiz']]
    await update.message.reply_text(texte, reply_markup=ReplyKeyboardMarkup(clavier, resize_keyboard=True), parse_mode="Markdown")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['search_active'] = True
    await update.message.reply_text("🔍 DEEP Activé ! Pose-moi ta question par texte ou en m'envoyant une note vocale 🎙️.")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = random.choice(QUIZ_DATA)
    context.user_data['current_quiz'] = quiz
    options = "\n".join(quiz["o"])
    await update.message.reply_text(f"🎮 *QUIZ*\n\n{quiz['q']}\n\n{options}\n\n👉 Réponds par A, B, C ou D.", parse_mode="Markdown")

# --- RECONNAISSANCE VOCALE SÉCURISÉE SANS CRASH ---
async def transcrire_vocal_direct(audio_bytes: bytes) -> str:
    try:
        headers = {
            'Authorization': 'Bearer 53LK64M6S3K66MZ3I6U6V6Y6X6Z6P3Z6',
            'Content-Type': 'audio/ogg',
        }
        url = "https://api.wit.ai/speech?v=20230215"
        response = requests.post(url, headers=headers, data=audio_bytes, timeout=20)
        
        if response.status_code == 200:
            lignes = response.text.strip().split('\n')
            if lignes:
                final_json = json.loads(lignes[-1])
                return final_json.get("text", "")
    except Exception as e:
        logger.error(f"Erreur Wit.ai : {e}")
    return ""

# --- GÉNÉRATEUR D'IMAGES ---
async def generer_image_ia(prompt_texte: str) -> io.BytesIO:
    try:
        prompt_en = GoogleTranslator(source='auto', target='en').translate(prompt_texte)
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt_en)}?width=1024&height=1024&nologo=true"
        response = requests.get(url, timeout=25)
        if response.status_code == 200: 
            return io.BytesIO(response.content)
    except: 
        return None

# --- MOTEUR DE TEXTE IA ---
async def appeler_ia_stable(prompt: str) -> str:
    try:
        url = f"https://text.pollinations.ai/{requests.utils.quote(prompt)}"
        response = requests.get(url, timeout=20)
        if response.status_code == 200: 
            return response.text
    except: 
        pass
    return "Mon moteur IA rencontre des difficultés."

# --- GESTIONNAIRE DES NOTES VOCALES ---
async def gerer_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if not user_data.get('search_active', False):
        await update.message.reply_text("⚠️ Appuie d'abord sur /search avant de m'envoyer une note vocale !")
        return
        
    await update.message.reply_text("🎧 Analyse de ta note vocale en cours...")
    try:
        fichier_vocal = await update.message.voice.get_file()
        vocal_bytes = await fichier_vocal.download_as_bytearray()
        
        # Traduction de la voix en texte
        texte_transcrit = await transcrire_vocal_direct(bytes(vocal_bytes))
        
        if not texte_transcrit:
            await update.message.reply_text("❌ Je n'ai pas bien entendu. Parle plus fort et distinctement s'il te plaît !")
            return
            
        await update.message.reply_text(f"🗣️ *Tu as dit :* \"_{texte_transcrit}_\"\n\n⚡ DEEP lance la recherche IA...", parse_mode="Markdown")
        
        # Recherche IA
        reponse_ia = await appeler_ia_stable(texte_transcrit)
        reponse_fr = GoogleTranslator(source='auto', target='fr').translate(reponse_ia)
        await update.message.reply_text(reponse_fr)
    except Exception as e:
        logger.error(f"Erreur vocal : {e}")
        await update.message.reply_text("❌ Erreur lors du traitement du message vocal.")

# --- GESTIONNAIRE MESSAGES TEXTE ---
async def gerer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte_recu = update.message.text.strip()
    texte_clean = texte_recu.lower()
    user_data = context.user_data
    
    if 'current_quiz' in user_data:
        quiz = user_data['current_quiz']
        if texte_recu.upper() in ["A", "B", "C", "D"]:
            if texte_recu.upper() == quiz["r"]: 
                await update.message.reply_text("🎉 Bonne réponse ! 👍")
            else: 
                await update.message.reply_text(f"❌ Raté ! C'était {quiz['r']}.")
            del user_data['current_quiz']
            return

    if texte_clean.startswith("imagine") or texte_clean.startswith("génère") or texte_clean.startswith("genere"):
        await update.message.reply_text("🎨 Génération de ton image en cours...")
        prompt_image = texte_recu.replace("imagine", "").replace("génère", "").replace("genere", "").strip()
        image_bytes = await generer_image_ia(prompt_image)
        if image_bytes: 
            await update.message.reply_photo(photo=image_bytes, caption=f"✨ Image pour : '{prompt_image}'")
        else: 
            await update.message.reply_text("❌ Erreur lors de la création de l'image.")
        return

    if calcul := alternatif_calcul(texte_recu):
        await update.message.reply_text(f"🧮 Résultat : `{calcul}`", parse_mode="Markdown")
        return

    if user_data.get('search_active', False):
        await update.message.reply_text("⚡ DEEP réfléchit...")
        reponse = await appeler_ia_stable(texte_recu)
        reponse_fr = GoogleTranslator(source='auto', target='fr').translate(reponse)
        await update.message.reply_text(reponse_fr)
    else:
        traduction = GoogleTranslator(source='auto', target='fr').translate(texte_recu)
        await update.message.reply_text(f"🌍 Traduction :\n{traduction}")

def alternatif_calcul(texte):
    try:
        caracteres = set("0123456789+-*/(). ")
        if not set(texte).issubset(caracteres): return None
        return str(eval(texte, {"__builtins__": None}, {}))
    except: return None

def main():
    print("🚀 DEEP V2.0 AUDIO REPARÉ...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.VOICE, gerer_vocal))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gerer_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
