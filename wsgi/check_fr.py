#!/usr/bin/python3

import sys
import helpers.sourcefile
import re

old_spelling = [
    "allége",
    "assiége",
    "avénement",
    "événement",
    "collége",
    "cortége",
    "liége",
    "piége",
    "privilége",
    "protége",
    "sacrilége",
    "siége",
    "solfége",
    "poëme",
    "poëte",
    "manége",
    "complétement",
    "incomplétement",
    "orfévre",
    ]

new_spelling = [
    "avènement"
    "évènement"
    "allège",
    "assiège",
    "collège",
    "cortège",
    "liège",
    "piège",
    "privilège",
    "protège",
    "sacrilège",
    "siège",
    "solfège",
    "poême",
    "poête",
    "manège"
    "complètement",
    "incomplètement",
    "orfèvre"
    ]

# Split a document in a list of words/punctuation
# ie. goes from "My name is Bond, James Bond!"
# into ['My', 'name', 'is', 'Bond', ',', 'James', 'Bond', '!']
def split_doc(doc):
    """Split the text into a list of words from the text."""

    # Split into list of words
    doc = re.findall(r'([\w-]+|\W)', doc)
    words = []

    for line in doc:
        line = line.strip()

        if line != '':
            words.append(line)

    return words


def clean_text(f):

    # Put spaces between 2 or more dashes.
    f.text = re.sub("(--+)", ' \1 ', f.text);
    f.text = re.sub("(_+)", ' _ ', f.text);

    return split_doc(f.text)


def check_fr(filename):

    print("FZ10")
    myfile = helpers.sourcefile.SourceFile()
    myfile.load_file(filename)

    # Get list of words
    words = clean_text(myfile)

    # Convertit en minuscules
    words = [ word.lower() for word in words]

    # Supprime les doublons
    words = list(set(words))

    # Trie la liste
    words = sorted(words)

    # Ancienne ortographe
    ancienne_ortographe = []
    for word in words:
        for spelling in old_spelling:
            if word.startswith(spelling):
                ancienne_ortographe.append((word, spelling))

    # Nouvelle ortographe
    nouvelle_ortographe = []
    for word in words:
        for spelling in new_spelling:
            if word.startswith(spelling):
                nouvelle_ortographe.append((word, spelling))

    # Mots finissant en "ens" et "ents"
    mots_ens = [ word for word in words if word.endswith("ens") and not word.endswith("iens") ]
    mots_ents = [ word for word in words if word.endswith("ents") and not word.endswith("ients") ]
    mots_ens_ents = [ mot + " / " + mot[:-1] + "ts" for mot in mots_ens if mot[:-1] + "ts" in mots_ents ]

    # Mots finissant en "ans" et "ants"
    mots_ans = [ word for word in words if word.endswith("ans") ]
    mots_ants = [ word for word in words if word.endswith("ants") ]
    mots_ans_ants = [ mot + " / " + mot[:-1] + "ts" for mot in mots_ans if mot[:-1] + "ts" in mots_ants ]

    return ancienne_ortographe, nouvelle_ortographe, mots_ens, mots_ents, mots_ens_ents, mots_ans, mots_ants, mots_ans_ants




def main():

    ancienne_ortographe, nouvelle_ortographe, mots_ens, mots_ents, mots_ens_ents, mots_ans, mots_ants, mots_ans_ants = check_fr(sys.argv[1])

    print("Ancienne ortographe:")
    print("====================")
    for word, spelling in ancienne_ortographe:
        print("%-30s (racine: %s)" % (word, spelling))

    print("\n\nNouvelle ortographe:")
    print("====================")
    for word, spelling in nouvelle_ortographe:
        print("%-30s (racine: %s)" % (word, spelling))


    print('\n\nMots finissant en "ens"')
    print("====================")
    for word in mots_ens:
        print(word)

    print('\n\nMots finissant en "ents"')
    print("====================")
    for word in mots_ents:
        print(word)

    print('\n\nLes 2 orthographes ens/ents')
    print("====================")
    for words in mots_ens_ents:
        print(words)

    print('\n\nMots finissant en "ans"')
    print("====================")
    for word in mots_ans:
        print(word)

    print('\n\nMots finissant en "ants"')
    print("====================")
    for word in mots_ants:
        print(word)

    print('\n\nLes 2 orthographes ans/ants')
    print("====================")
    for words in mots_ans_ants:
        print(words)



if __name__ == "__main__":
    main()
