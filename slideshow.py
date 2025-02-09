import gurobipy as gp
from gurobipy import GRB
from itertools import combinations
import sys

# Lecture du fichier
def lire_fichier(nom_fichier):
    try:
        with open(nom_fichier, 'r') as fichier:
            nb_photos = int(fichier.readline().strip())
            images = {}
            verticales = []
            horizontales = []
            for num_image, ligne in enumerate(fichier):
                elements = ligne.split()
                format_photo = elements[0]
                tags = set(elements[2:])
                images[num_image] = {'format': format_photo, 'tags': tags}
                if format_photo == 'V':
                    verticales.append(num_image)
                else:
                    horizontales.append(num_image)
        return nb_photos, images, verticales, horizontales
    except FileNotFoundError:
        print(f"Erreur: Le fichier {nom_fichier} est introuvable.")
        sys.exit(1)

# Fonction pour calculer le score entre deux slides
def interest_factor(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# Chargement des données depuis le fichier passé en argument
if len(sys.argv) != 2:
    sys.exit(1)

dataset = sys.argv[1]
nb_photos, images, verticales, horizontales = lire_fichier(dataset)

# Génération des slides possibles
slides = []
slide_tags = {}
slide_photo_count = {}

# Ajout des slides horizontaux
for img in horizontales:
    slide = (img,)
    slides.append(slide)
    slide_tags[slide] = images[img]['tags']
    slide_photo_count[slide] = 1

# Ajout des slides verticaux (par paires)
for i, j in combinations(verticales, 2):
    slide = (i, j)
    slides.append(slide)
    slide_tags[slide] = images[i]['tags'] | images[j]['tags']
    slide_photo_count[slide] = 2

# Création du modèle
model = gp.Model("SlideShow")

# Variables de décision
# Un slide est utilisé ou non
slide_vars = model.addVars(slides, vtype=GRB.BINARY, name="slide")

# Variables d'ordre pour les slides sélectionnés
slide_order = model.addVars(slides, vtype=GRB.CONTINUOUS, name="order")

# Contraintes
# Une photo est utilisée maximum 1 fois
photo_constraints = {i: model.addConstr(
    gp.quicksum(slide_vars[s] for s in slides if i in s) <= 1,
    name=f"photo_{i}")
    for i in range(nb_photos)
}

# Ordre des slides
for s1, s2 in combinations(slides, 2):
    if s1 != s2:
        model.addConstr(
            slide_order[s1] + 1 <= slide_order[s2] + len(slides) * (1 - slide_vars[s1] - slide_vars[s2]),
            name=f"order_{s1}_{s2}"
        )

# Objectif
# Maximiser le score basé sur l'ordre correct des slides sélectionnés
model.setObjective(
    gp.quicksum(interest_factor(slide_tags[s1], slide_tags[s2]) * slide_vars[s1] * slide_vars[s2]
                for s1, s2 in combinations(slides, 2)),
    GRB.MAXIMIZE
)

# Résolution
model.optimize()

# Extraction de la solution dans l'ordre des slides sélectionnés
selected_slides = [s for s in slides if slide_vars[s].X > 0.5]
slides_solution = sorted(selected_slides, key=lambda s: slide_order[s].X)

# Score optimal
total_score = model.objVal

# Sauvegarde de la solution dans un fichier .sol
with open("slideshow.sol", "w") as f:
    f.write(f"{len(slides_solution)}\n")
    for slide in slides_solution:
        f.write(" ".join(map(str, slide)) + "\n")

print(f"Solution optimale écrite dans slideshow.sol avec un score de {total_score}")
