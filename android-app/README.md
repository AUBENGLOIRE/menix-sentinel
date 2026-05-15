# MENIX Sentinel UI — App Android (Kotlin)

App native légère qui sert de **dashboard** au boîtier Sentinel.

## Ce qu'elle fait
- Affiche en **temps réel** les capteurs (gaz, O₂, CO, temp, batterie) lus depuis
  `/sdcard/menix-sentinel/data/sensors_live.json` (mis à jour par `mock/esp32_mock.py` toutes les 2 s).
- Boutons gros doigts pour : **Torche ON/OFF**, **SOS**, **Photo**, **Stop**.
- Chaque bouton lance un script Termux via `RUN_COMMAND` Intent (Termux:API).
- Bandeau d'**alerte** rouge clignotant quand un seuil est dépassé.

## Prérequis
1. Termux + Termux:API installés.
2. Dans Termux : `echo "allow-external-apps=true" >> ~/.termux/termux.properties`
3. Lien symbolique : `ln -s ~/menix-sentinel/data /sdcard/menix-sentinel/data`
   (ou modifier le chemin dans `MainActivity.kt`)

## Build
Ouvrir le dossier dans Android Studio (Giraffe+), brancher le téléphone, **Run**.
APK debug suffit pour la démo.

## Structure
```
android-app/
├── build.gradle.kts            (root)
├── settings.gradle.kts
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/ymeni/menix/
│       │   ├── MainActivity.kt
│       │   ├── SensorRepo.kt
│       │   └── TermuxBridge.kt
│       └── res/
│           ├── layout/activity_main.xml
│           └── values/{strings.xml,colors.xml,themes.xml}
```
