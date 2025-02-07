import gurobipy as gp
from gurobipy import GRB
from itertools import combinations
from functools import partial

# Lecture du fichier
def lire_fichier(nom_fichier):
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

# Fonction pour calculer le score entre deux slides
def interest_factor(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# Callback pour arrêter après 15 itérations sans amélioration ou après 60 secondes
class CallbackData:
    def __init__(self):
        self.last_gap_change_time = -GRB.INFINITY
        self.last_gap = GRB.INFINITY

def callback(model, where, *, cbdata):
    if where != GRB.Callback.MIP:
        return
    if model.cbGet(GRB.Callback.MIP_SOLCNT) == 0:
        return

    best = model.cbGet(GRB.Callback.MIP_OBJBST)
    bound = model.cbGet(GRB.Callback.MIP_OBJBND)
    gap = abs((bound - best) / best) if best != 0 else GRB.INFINITY
    time = model.cbGet(GRB.Callback.RUNTIME)
    if gap < cbdata.last_gap - 1e-4:
        cbdata.last_gap = gap
        cbdata.last_gap_change_time = time
        return

    if time - cbdata.last_gap_change_time > 15:
        print("Stopping optimization: No improvement for 15 iterations")
        model.terminate()

# Chargement des données
nb_photos, images, verticales, horizontales = lire_fichier('PetPics-20.txt')

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

# Ajout des slides verticaux
for i, j in combinations(verticales, 2):
    slide = (i, j)
    slides.append(slide)
    slide_tags[slide] = images[i]['tags'] | images[j]['tags']
    slide_photo_count[slide] = 2

# Création du modèle
model = gp.Model("SlideShow")
model.setParam('TimeLimit', 60)

# Variable de décision
slide_vars = model.addVars(slides, vtype=GRB.BINARY, name="slide")

# Objectif
model.setObjective(
    gp.quicksum(interest_factor(slide_tags[s1], slide_tags[s2]) * slide_vars[s1] * slide_vars[s2]
                for s1, s2 in combinations(slides, 2)), GRB.MAXIMIZE
)

# Contraintes
model.addConstr(
    gp.quicksum(slide_photo_count[s] * slide_vars[s] for s in slides) == nb_photos,
    "nombre_total_photos"
)

# Définition et exécution de l'optimisation avec callback
callback_data = CallbackData()
callback_func = partial(callback, cbdata=callback_data)
model.optimize(callback_func)

# Extraction de la solution
slides_solution = [s for s in slides if slide_vars[s].x > 0.5]
total_score = sum(interest_factor(slide_tags[s1], slide_tags[s2])
                  for s1, s2 in zip(slides_solution, slides_solution[1:]))

# Sauvegarde de la solution
with open("slideshow.sol", "w") as f:
    f.write(f"{len(slides_solution)}\n")
    for slide in slides_solution:
        f.write(" ".join(map(str, slide)) + "\n")
    f.write(f"Score total: {total_score}\n")

print(f"Solution optimale écrite dans slideshow.sol avec un score de {total_score}")
