CREATE TABLE Revue (
    id_Titre INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
    Titre VARCHAR(255) NOT NULL,
    Contributeur VARCHAR(255),
    Langue VARCHAR(255),
    Identifiant VARCHAR(255) COMMENT 'URL à extraire lors du scrapping',
    Source VARCHAR(255) COMMENT 'catégorise le rangement dans la bibliothèque numérique de la BNF',
    Source_détail VARCHAR(255),
    Date_de_mise_en_ligne DATE,
    Conservation_numerique VARCHAR(255),
    Date_d_edition INTEGER,
    URL VARCHAR(255),
    PRIMARY KEY (id_Titre)
);

CREATE TABLE Auteur (
    id_Auteur INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
    Auteur TEXT(65535),
    PRIMARY KEY (id_Auteur)
);

CREATE TABLE Editeur (
    id_Editeur INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
    Nom VARCHAR(255),
    Lieu VARCHAR(255),
    Editeur_details TEXT(65535),
    PRIMARY KEY (id_Editeur)
) COMMENT='champ ville à extraire des données entre parenthèses dans le Json';

CREATE TABLE Sujet (
    id_Sujet INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
    Sujet VARCHAR(255),
    PRIMARY KEY (id_Sujet)
);

-- Tables de jonction 
CREATE TABLE Revue_Auteur (
    id_Titre INTEGER NOT NULL,
    id_Auteur INTEGER NOT NULL,
    PRIMARY KEY (id_Titre, id_Auteur),
    FOREIGN KEY (id_Titre) REFERENCES Revue(id_Titre) ON DELETE CASCADE,
    FOREIGN KEY (id_Auteur) REFERENCES Auteur(id_Auteur) ON DELETE CASCADE
);

CREATE TABLE Revue_Sujet (
    id_Titre INTEGER NOT NULL,
    id_Sujet INTEGER NOT NULL,
    PRIMARY KEY (id_Titre, id_Sujet),
    FOREIGN KEY (id_Titre) REFERENCES Revue(id_Titre) ON DELETE CASCADE,
    FOREIGN KEY (id_Sujet) REFERENCES Sujet(id_Sujet) ON DELETE CASCADE
);

CREATE TABLE Revue_Editeur (
    id_Titre INTEGER NOT NULL,
    id_Editeur INTEGER NOT NULL,
    PRIMARY KEY (id_Titre, id_Editeur),
    FOREIGN KEY (id_Titre) REFERENCES Revue(id_Titre) ON DELETE CASCADE,
    FOREIGN KEY (id_Editeur) REFERENCES Editeur(id_Editeur) ON DELETE CASCADE
);
