import gurobipy as gp
from gurobipy import GRB
from itertools import combinations
import sys

# méthode pour lire le fichier
def lireFichier(nom_fichier):
    try:
        with open(nom_fichier, 'r') as fichier:
            nbPhotos = int(fichier.readline().strip())
            images = {}
            verticales = []
            horizontales = []
            for numImage, ligne in enumerate(fichier):
                elements = ligne.split()
                format_photo = elements[0]
                tags = set(elements[2:])
                images[numImage] = {'format': format_photo, 'tags': tags}
                if format_photo == 'V':
                    verticales.append(numImage)
                else:
                    horizontales.append(numImage)
        return nbPhotos, images, verticales, horizontales
    except FileNotFoundError:
        print(f"Erreur: Le fichier {nom_fichier} est introuvable.")
        sys.exit(1)

# méthode pour calculer le score d'une slide
def scoreSlide(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# chargement des données
if len(sys.argv) != 2:
    sys.exit(1)
dataset = sys.argv[1]
nbPhotos, images, verticales, horizontales = lireFichier(dataset)

# génération des slides possibles
slides = []
slideTags = {}
slidePhotoCount = {}

# ajout des slides horizontales
for img in horizontales:
    slide = (img,)
    slides.append(slide)
    slideTags[slide] = images[img]['tags']
    slidePhotoCount[slide] = 1

# ajout des slides verticales (toutes les combinaisons possibles)
for i, j in combinations(verticales, 2):
    slide = (i, j)
    slides.append(slide)
    slideTags[slide] = images[i]['tags'] | images[j]['tags']
    slidePhotoCount[slide] = 2

# on calcule au préalable les scores de transitions entre chaque paire de slides
transitionScore = {(s1, s2): scoreSlide(slideTags[s1], slideTags[s2])
                    for s1 in slides for s2 in slides if s1 != s2}

model = gp.Model("SlideShow")

# variables de décision :
# 1 si la slide est utilisée dans le diaporama, 0 sinon
x = model.addVars(slides, vtype=GRB.BINARY, name="x")
# 1 si la slide 1 suit la slide 2, 0 sinon
y = model.addVars(transitionScore.keys(), vtype=GRB.BINARY, name="y")

# contraintes :
# une slide n'a pas plus d'un successeur et un prédécesseur
for s in slides:
    model.addConstr(gp.quicksum(y[s, s2] for s2 in slides if s2 != s) <= x[s],
                    name=f"successeur_{s}")
    model.addConstr(gp.quicksum(y[s1, s] for s1 in slides if s1 != s) <= x[s],
                    name=f"predecesseur_{s}")


for photo in range(nbPhotos):
    slidesWithPhoto = []
    # pour chaque slide, on vérifie si la photo est présente dans cette slide
    for s in slides:
        # si c'est le cas on l'ajoute la slide à la liste
        if photo in s:
            slidesWithPhoto.append(s)

    # une image est utilisée au plus une fois dans le diaporama
    if slidesWithPhoto:
        model.addConstr(gp.quicksum(x[s] for s in slidesWithPhoto) <= 1,
                        name=f"photo_{s}")

# le diaporama doit contenir minimum une slide
model.addConstr(gp.quicksum(x[s] for s in slides) >= 1, name="nbMinSlide")

# variable de précédence
varPrec = model.addVars(slides, vtype=GRB.CONTINUOUS, lb=0, ub=len(slides), name="u")
# on établit les contraintes de précédences
for s1, s2 in y:
    if s1 != s2:
        model.addConstr(varPrec[s1] - varPrec[s2] + len(slides) * y[s1, s2] <= len(slides) - 1,
                        name=f"precedence_{s1}_{s2}")


# objectif :
# maximiser la somme des scores de transition pour les slides qui se succèdent
model.setObjective(gp.quicksum(transitionScore[s1, s2] * y[s1, s2]
                               for (s1, s2) in y), GRB.MAXIMIZE)

model.optimize()


# reconstruction du diaporama à partir de la solution obtenue par le modèle
# recherche de la première slide du diaporama
startSlide = None
for s in slides:
    if x[s].X == 1 and sum(y[s1, s].X for s1 in slides if s1 != s) == 0:
        startSlide = s
        break

diaporama = []

# si on a une première slide, on construit le diaporama à partir de cette slide
if startSlide is not None:
    diaporama.append(startSlide) 
    currentSlide = startSlide

    # on cherche des slides pour continuer à construire le diaporama
    while True:
        slideSuivante = None

        # pour chaque slide, on vérifie si elle suit la current slide
        for s in slides:
            # si on a une transition entre current slide et s alors s suit current slide
            if s != currentSlide and y[currentSlide, s].X == 1:
                slideSuivante = s
                break

        # si aucune slide suivante n'est trouvée, c'est que le diaporama est terminé
        if slideSuivante is None:
            break

        # tant qu'on a une slide suivante on l'ajoute au diaporama
        diaporama.append(slideSuivante)
        currentSlide = slideSuivante

# calcul du score total du diaporama
scoreTotal = sum(
    scoreSlide(slideTags[s1], slideTags[s2])
    for s1, s2 in zip(diaporama, diaporama[1:])
)

print(f"Solution optimale écrite dans slideshow.sol avec un score de {scoreTotal}.")

# ecriture de la solution dans un fichier .sol
with open("slideshow.sol", "w") as f:
    f.write(f"{len(diaporama)}\n")
    for slide in diaporama:
        f.write(" ".join(map(str, slide)) + "\n")
