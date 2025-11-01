# System Tray Icon

## Conversion SVG vers PNG

Pour convertir l'icône SVG en PNG pour le system tray Ubuntu :

```bash
# Installer ImageMagick ou Inkscape
sudo apt install imagemagick

# Convertir l'icône
convert -background none tray_icon.svg -resize 64x64 tray_icon.png

# Alternative avec Inkscape (meilleure qualité)
sudo apt install inkscape
inkscape tray_icon.svg --export-filename=tray_icon.png --export-width=64 --export-height=64
```

## Formats supportés

- **SVG** : Format vectoriel source (modifiable)
- **PNG** : Format utilisé par le system tray (64x64 pixels recommandé)

## Personnalisation

Vous pouvez éditer `tray_icon.svg` avec :
- Inkscape (GUI) : `sudo apt install inkscape && inkscape tray_icon.svg`
- N'importe quel éditeur de texte pour modifier les couleurs ou formes
