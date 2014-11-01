#!/usr/bin/python3

import sys
import helpers.sourcefile
import re

old_spelling = [
    "allége",
    "assiége",
    "avénement",
    "collége",
    "complétement",
    "cortége",
    "déréglement",
    "entiérement",
    "incomplétement",
    "liége",
    "manége",
    "orfévre",
    "piége",
    "poëme",
    "poëte",
    "privilége",
    "protége",
    "sacrilége",
    "siége",
    "solfége",
    "sortilége",
    "événement",
    ]

new_spelling = [
    "allège",
    "assiège",
    "avènement"
    "collège",
    "complètement",
    "cortège",
    "dérèglement",
    "entièrement",
    "incomplètement",
    "liège",
    "manège"
    "orfèvre",
    "piège",
    "poême",
    "poête",
    "privilège",
    "protège",
    "sacrilège",
    "siège",
    "solfège",
    "sortilège",
    "évènement"
    ]

# Split a document in a list of words/punctuation
# ie. goes from "My name is Bond, James Bond!"
# into ['My', 'name', 'is', 'Bond', ',', 'James', 'Bond', '!']
def split_doc(text):
    """Split the text into a list of words from the text."""

    # Put spaces between 2 or more dashes.
    text = re.sub("(--+)", ' \1 ', text);
    text = re.sub("(_+)", ' _ ', text);

    # Split into list of words
    text = re.findall(r'([\w-]+|\W)', text)
    words = []

    for line in text:
        line = line.strip()

        if line != '':
            words.append(line)

    return words


def check_fr(filename):

    myfile = helpers.sourcefile.SourceFile()
    raw, text, enc = myfile.load_file(filename)

    if not raw:
        return None, None, None, None, None, None, None, None

    # Get list of words
    words = split_doc(text)

    # Convertit en minuscules
    words = [ word.lower() for word in words]

    # Supprime les doublons
    words = list(set(words))

    # Trie la liste
    words = sorted(words)

    # Ancienne orthographe
    ancienne_orthographe = []
    for word in words:
        for spelling in old_spelling:
            if word.startswith(spelling):
                ancienne_orthographe.append((word, spelling))

    # Nouvelle orthographe
    nouvelle_orthographe = []
    for word in words:
        for spelling in new_spelling:
            if word.startswith(spelling):
                nouvelle_orthographe.append((word, spelling))

    # Mots finissant en "ens" et "ents"
    mots_ens = [ word for word in words if word.endswith("ens") and not word.endswith("iens") ]
    mots_ents = [ word for word in words if word.endswith("ents") and not word.endswith("ients") ]
    mots_ens_ents = [ mot + " / " + mot[:-1] + "ts" for mot in mots_ens if mot[:-1] + "ts" in mots_ents ]

    # Mots finissant en "ans" et "ants"
    mots_ans = [ word for word in words if word.endswith("ans") ]
    mots_ants = [ word for word in words if word.endswith("ants") ]
    mots_ans_ants = [ mot + " / " + mot[:-1] + "ts" for mot in mots_ans if mot[:-1] + "ts" in mots_ants ]

    return ancienne_orthographe, nouvelle_orthographe, mots_ens, mots_ents, mots_ens_ents, mots_ans, mots_ants, mots_ans_ants




def main():

    ancienne_orthographe, nouvelle_orthographe, mots_ens, mots_ents, mots_ens_ents, mots_ans, mots_ants, mots_ans_ants = check_fr(sys.argv[1])

    print("Ancienne orthographe:")
    print("====================")
    for word, spelling in ancienne_orthographe:
        print("%-30s (racine: %s)" % (word, spelling))

    print("\n\nNouvelle orthographe:")
    print("====================")
    for word, spelling in nouvelle_orthographe:
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
