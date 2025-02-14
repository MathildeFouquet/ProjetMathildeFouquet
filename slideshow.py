import gurobipy as gp
from gurobipy import GRB
from itertools import combinations
import sys

# méthode pour lire le fichier
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

# méthode pour calculer le score d'une slide
def score_slide(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# Chargement des données
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

# Variables de décision :
# Variable binaire : 1 si la diapositive s est assigné à la position p, 0 sinon
slide_pos_vars = model.addVars([(s, p) for s in slides for p in range(len(slides))],
                              vtype=GRB.BINARY, name="slide_pos")

# Contraintes
# Une photo est utilisée maximum 1 fois
for i in range(nb_photos):
    model.addConstr(
        gp.quicksum(slide_pos_vars[s, p]
                   for s in slides if i in s
                   for p in range(len(slides))) <= 1,
        name=f"photo_{i}")

# Chaque position ne peut avoir qu'une seule slide
for p in range(len(slides)):
    model.addConstr(
        gp.quicksum(slide_pos_vars[s, p] for s in slides) <= 1,
        name=f"pos_{p}")

# Une slide ne peut être utilisée qu'une seule fois
for s in slides:
    model.addConstr(
        gp.quicksum(slide_pos_vars[s, p] for p in range(len(slides))) <= 1,
        name=f"slide_{s}")

# Contrainte d'ordre
for p in range(1, len(slides)):
    model.addConstr(
        gp.quicksum(slide_pos_vars[s, p] for s in slides) <=
        gp.quicksum(slide_pos_vars[s, p-1] for s in slides),
        name=f"order_{p}")

# Objectif
# Maximiser le score du diaporama
objective = gp.quicksum(
    score_slide(slide_tags[s1], slide_tags[s2]) * slide_pos_vars[s1, p] * slide_pos_vars[s2, p+1]
    for s1 in slides
    for s2 in slides
    for p in range(len(slides)-1)
)
model.setObjective(objective, GRB.MAXIMIZE)

# Permet d'afficher le progrès dans la console
model.Params.OutputFlag = 1

# Prends tous les coeurs disponibles
model.setParam("Threads", 0)

# Gap optimalité pour accélérer la convergence
model.setParam("MIPGap", 0.01)

# Utilise plusieurs méthodes de résolution en parallèle
model.setParam("ConcurrentMIP", 2)

# Privilégie des solutions rapidement
model.setParam("MIPFocus", 1)

model.optimize()

# Extraction de la solution
slides_solution = []
for p in range(len(slides)):
    for s in slides:
        if slide_pos_vars[s, p].X > 0.5:
            slides_solution.append(s)
            break
    if len(slides_solution) < p + 1:
        break

# Calcul du score total
total_score = sum(
    score_slide(slide_tags[s1], slide_tags[s2])
    for s1, s2 in zip(slides_solution, slides_solution[1:])
)

print(f"Score total: {total_score}")

# Ecriture de la solution dans un fichier .sol
with open("slideshow.sol", "w") as f:
    f.write(f"{len(slides_solution)}\n")
    for slide in slides_solution:
        f.write(" ".join(map(str, slide)) + "\n")
