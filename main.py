import logging
import nest_asyncio
import os
import g4f
import requests
import urllib.parse
import time
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration de sécurité indispensable sur Google Colab
nest_asyncio.apply()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

LANGUES_DICT = {
    "anglais": "en", "🇺🇸": "en", "🇬🇧": "en",
    "français": "fr", "france": "fr", "🇫🇷": "fr",
    "espagnol": "es", "🇪🇸": "es",
    "allemand": "de", "🇩🇪": "de",
    "italien": "it", "🇮🇹": "it",
    "arabe": "ar", "🇸🇦": "ar"
}

# --- MISE À JOUR : Accueil personnalisé ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['attente_recherche'] = False
    
    # Récupération automatique du prénom de l'utilisateur Telegram
    nom_utilisateur = update.effective_user.first_name
    
    message = (
        f"🤖 **Bienvenue sur DEEP, {nom_utilisateur} !** 🚀\n\n"
        "🎙️ **Nouveau :** Tu peux m'envoyer des notes vocales directement !\n"
        "🔍 **Pour activer l'IA en continu :** Appuie sur **/search** !\n"
        "🧮 **Pour un calcul rapide :** Écris-le directement.\n"
        "🖼️ **Pour générer une image :** Écris '*imagine...*' ou '*génère...*'"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['attente_recherche'] = True
    await update.message.reply_text("🔍 **DEEP Activé**", parse_mode="Markdown")

# --- LE TRAITEMENT DE TEXTE CENTRAL DE DEEP ---
async def analyser_et_repondre(texte_recu, update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = texte_recu.strip()
    texte_minuscule = texte.lower()
    
    # --- 1. SÉCURITÉ MAXIMUM POUR LA GÉNÉRATION D'IMAGES ---
    if texte_minuscule.startswith("imagine") or texte_minuscule.startswith("génère") or texte_minuscule.startswith("genere"):
        description = texte.split(' ', 1)[1] if ' ' in texte else ""
        if not description:
            await update.message.reply_text("❌ Donne-moi une description ! Exemple : `imagine une maison`")
            return
            
        await update.message.reply_text("🎨 *DEEP dessine ton image, patiente quelques secondes...*", parse_mode="Markdown")
        
        try:
            description_en = GoogleTranslator(source='auto', target='en').translate(description)
            prompt_url = urllib.parse.quote(description_en)
            url_image = f"https://image.pollinations.ai/p/{prompt_url}?width=1080&height=1080&nologo=true"
            
            # --- LE SYSTÈME DE TRIPLE TENTATIVE (RETRY) ---
            reponse_image = None
            for tentative in range(3):  # Essaie jusqu'à 3 fois si le serveur est fatigué
                try:
                    reponse_image = requests.get(url_image, timeout=20)
                    if reponse_image.status_code == 200:
                        break  # Succès ! On sort de la boucle de secours
                except requests.exceptions.RequestException:
                    pass
                time.sleep(2)  # Petite pause de sécurité avant de réessayer
                
            if reponse_image and reponse_image.status_code == 200:
                photo_flux = BytesIO(reponse_image.content)
                photo_flux.name = 'deep_image.jpg'
                await update.message.reply_photo(photo=photo_flux, caption=f"🖼️ **Image générée par DEEP pour :**\n_\"{description}\"_", parse_mode="Markdown")
            else:
                # Si après 3 essais ça ne veut vraiment pas, on donne une réponse polie et propre
                await update.message.reply_text("✨ *Le serveur de dessin est un peu saturé à l'instant. Réessaye ta demande dans quelques secondes !*")
            return
            
        except Exception as e:
            await update.message.reply_text("❌ Une petite erreur est survenue. Relance ta commande d'image !")
            print(f"Erreur Image : {e}")
            return

    # --- 2. LES CALCULS RAPIDES ---
    if any(char in texte for char in "+-*/0123456789") and len(texte) < 15:
        try:
            calcul_propre = texte.replace("x", "*").replace(":", "/")
            resultat = eval(calcul_propre, {"__builtins__": None}, {})
            await update.message.reply_text(f"🧮 **DEEP Calcul :**\n`{texte}` = **{resultat}**", parse_mode="Markdown")
            return
        except:
            pass 

    # --- SÉCURITÉ DU MODE ACTIVÉ ---
    if not context.user_data.get('attente_recherche'):
        await update.message.reply_text("Pour activer mon intelligence, appuie d'abord sur /search 🔍")
        return

    # --- 3. LE TRADUCTEUR RAPIDE ---
    cible_langue = None
    for mot_cle, code in LANGUES_DICT.items():
        if mot_cle in texte_minuscule:
            cible_langue = code
            break

    if cible_langue:
        try:
            nettoyage = texte
            mots_traduction = ["traduis", "traduit", "traduire", "en anglais", "en espagnol", "en allemand", "en français", "en italien", "en arabe"]
            for m in mots_traduction:
                nettoyage = nettoyage.lower().replace(m, "").strip()
            for k in LANGUES_DICT.keys():
                nettoyage = nettoyage.replace(k, "").strip()

            traduction = GoogleTranslator(source='auto', target=cible_langue).translate(nettoyage)
            await update.message.reply_text(f"🌐 **DEEP Traduction :**\n\n{traduction}")
            return
        except Exception as e:
            print(f"Erreur Traducteur : {e}")

    # --- 4. LE CERVEAU IA ---
    await update.message.reply_text("⏳ *DEEP réfléchit...*", parse_mode="Markdown")
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[
                {"role": "system", "content": "Tu es DEEP, un bot Telegram intelligent. Réponds toujours de manière claire, vivante et synthétique en français."},
                {"role": "user", "content": texte}
            ]
        )
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Désolé, je n'ai pas pu formuler de réponse.")
    except Exception as e:
        await update.message.reply_text("Moteur DEEP indisponible pour le moment.")
        print(f"Erreur IA : {e}")

async def gerer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await analyser_et_repondre(update.message.text, update, context)

async def gerer_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ *DEEP écoute ton message vocal...*", parse_mode="Markdown")
    
    try:
        fichier_audio = await context.bot.get_file(update.message.voice.file_id)
        chemin_ogg = "vocal_temp.ogg"
        chemin_wav = "vocal_temp.wav"
        
        await fichier_audio.download_to_drive(chemin_ogg)
        
        audio = AudioSegment.from_ogg(chemin_ogg)
        audio.export(chemin_wav, format="wav")
        
        reconnaisseur = sr.Recognizer()
        with sr.AudioFile(chemin_wav) as source:
            donnees_audio = reconnaisseur.record(source)
            texte_transcrit = reconnaisseur.recognize_google(donnees_audio, language="fr-FR")
            
        if os.path.exists(chemin_ogg): os.remove(chemin_ogg)
        if os.path.exists(chemin_wav): os.remove(chemin_wav)
        
        await update.message.reply_text(f"🗣️ **Ce que j'ai compris :**\n_\"{texte_transcrit}\"_", parse_mode="Markdown")
        await analyser_et_repondre(texte_transcrit, update, context)

    except sr.UnknownValueError:
        await update.message.reply_text("❌ Désolé, le son n'était pas assez clair. Répète un peu plus fort !")
    except Exception as e:
        await update.message.reply_text("❌ Impossible de lire cette note vocale pour le moment.")
        print(f"Erreur Système Audio : {e}")

def main():
    # METS TON TOKEN TELEGRAM ENTRE LES GUILLEMETS CI-DESSOUS
    TOKEN = "8402606079:AAE74zmoeXlBehpOOsRAa2O3OkyM0ze1wSA"
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gerer_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, gerer_vocal))

    print("---------------------------------------------")
    print("🚀 DEEP V3.2 PARFAIT - BIENVENUE PERSONNALISÉE ET BLINDAGE OK !")
    print("---------------------------------------------")
    application.run_polling(close_loop=False)

if __name__ == '__main__':
    main()
