from gtts import gTTS
import base64

def audio_ia(texte):
    voix = gTTS(
        texte,
        lang="fr"
    )

    fichier = "betscope.mp3"
    voix.save(fichier)

    with open(fichier, "rb") as f:
        audio = base64.b64encode(
            f.read()
        ).decode()

    return f"""
    <audio controls>
    <source src="data:audio/mp3;base64,{audio}">
    </audio>
    """
  
