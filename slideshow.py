import gurobipy as gp
from gurobipy import GRB

with open('trivial.txt', 'r') as fichier:
    nbPhotos = int(fichier.readline().strip())
    # Dictionnaire pour stocker les informations de chaque image
    images = {}
    diapo = []
    slides = []
    # Lecture des lignes avec énumération
    for num_image, ligne in enumerate(fichier, start=1):  # start=1 pour commencer à 1
        elements = ligne.split()
        format_photo = elements[0]  # H ou V
        nb_tags = int(elements[1])  # Nombre de tags
        tags = elements[2:]  # Liste des tags

        # Stockage dans le dictionnaire avec le numéro d'image comme clé
        images[num_image] = {
            'format': format_photo,
            'nb_tags': nb_tags,
            'tags': tags
        }


model = gp.Model("Slide show")
x = model.addVars(num_image, format_photo, slides, vtype=GRB.BINARY, name="x")

