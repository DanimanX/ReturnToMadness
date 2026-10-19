"""Genera assets/lang/{es,en,fr,pt,it}.json.

Una sola tabla con las cinco versiones por clave evita desincronizar idiomas:
si falta una traducción, el script falla y no escribe nada.
"""
from __future__ import annotations

import json
import os

LANGS = ["es", "en", "fr", "pt", "it"]
NAMES = {
    "es": "ESPAÑOL", "en": "ENGLISH", "fr": "FRANÇAIS",
    "pt": "PORTUGUÊS", "it": "ITALIANO",
}

E = {
    # ---------------------------------------------------------------- título
    "app.title": (
        "REGRESO A LA LOCURA", "RETURN TO MADNESS", "RETOUR À LA FOLIE",
        "REGRESSO À LOUCURA", "RITORNO ALLA FOLLIA"),
    "app.tagline1": (
        "SIETE DESCENSOS. UNA SOLA CORDURA.",
        "SEVEN DESCENTS. ONE SINGLE SANITY.",
        "SEPT DESCENTES. UNE SEULE RAISON.",
        "SETE DESCENSOS. UMA SÓ SANIDADE.",
        "SETTE DISCESE. UNA SOLA RAGIONE."),
    "app.tagline2": (
        "EL QUE MIRA TAMBIÉN ES MIRADO.",
        "HE WHO WATCHES IS ALSO WATCHED.",
        "CELUI QUI REGARDE EST REGARDÉ AUSSI.",
        "QUEM OLHA TAMBÉM É OLHADO.",
        "CHI GUARDA È GUARDATO A SUA VOLTA."),
    "app.press_enter": (
        "PRESIONA ENTER PARA DESCENDER",
        "PRESS ENTER TO DESCEND",
        "APPUIE SUR ENTRÉE POUR DESCENDRE",
        "PRIME ENTER PARA DESCER",
        "PREMI INVIO PER SCENDERE"),
    "app.press_continue": (
        "PRESIONA ENTER PARA CONTINUAR",
        "PRESS ENTER TO CONTINUE",
        "APPUIE SUR ENTRÉE POUR CONTINUER",
        "PRIME ENTER PARA CONTINUAR",
        "PREMI INVIO PER CONTINUARE"),
    "app.reset_hint": (
        "O PULSA SUPR PARA EMPEZAR DE NUEVO",
        "OR PRESS DELETE TO START OVER",
        "OU SUPPR POUR RECOMMENCER",
        "OU PRESSIONA DELETE PARA RECOMEÇAR",
        "OPPURE PREMI CANC PER RICOMINCIARE"),
    "promo.made_by": (
        "Un juego de DanimanX", "A game by DanimanX", "Un jeu de DanimanX",
        "Um jogo de DanimanX", "Un gioco di DanimanX"),
    "promo.tagline": (
        "Siete descensos.\nUna sola cordura.",
        "Seven descents.\nOne single sanity.",
        "Sept descentes.\nUne seule raison.",
        "Sete descensos.\nUma só sanidade.",
        "Sette discese.\nUna sola ragione."),
    "promo.built": (
        "Godot 4\nArte, audio y niveles generados",
        "Godot 4\nArt, audio and levels generated",
        "Godot 4\nArt, audio et niveaux générés",
        "Godot 4\nArte, áudio e níveis gerados",
        "Godot 4\nArte, audio e livelli generati"),
    "promo.langs": (
        "ESPAÑOL · ENGLISH\nFRANÇAIS · PORTUGUÊS · ITALIANO",
        "SPANISH · ENGLISH\nFRENCH · PORTUGUESE · ITALIAN",
        "ESPAGNOL · ANGLAIS\nFRANÇAIS · PORTUGAIS · ITALIEN",
        "ESPANHOL · INGLÊS\nFRANCÊS · PORTUGUÊS · ITALIANO",
        "SPAGNOLO · INGLESE\nFRANCESE · PORTOGHESE · ITALIANO"),
    "app.credit": (
        "GODOT 4 · ARTE Y AUDIO GENERADOS",
        "GODOT 4 · ART AND AUDIO GENERATED",
        "GODOT 4 · ART ET AUDIO GÉNÉRÉS",
        "GODOT 4 · ARTE E ÁUDIO GERADOS",
        "GODOT 4 · ARTE E AUDIO GENERATI"),

    # ------------------------------------------------------------------- hud
    "ui.clarity": ("CORDURA", "SANITY", "RAISON", "SANIDADE", "RAGIONE"),
    "ui.madness": ("LOCURA", "MADNESS", "FOLIE", "LOUCURA", "FOLLIA"),
    "ui.paused": ("PAUSA", "PAUSED", "PAUSE", "PAUSA", "PAUSA"),
    "ui.fragment": (
        "FRAGMENTO RECUPERADO", "FRAGMENT RECOVERED", "FRAGMENT RETROUVÉ",
        "FRAGMENTO RECUPERADO", "FRAMMENTO RECUPERATO"),
    "ui.lang_label": ("IDIOMA", "LANGUAGE", "LANGUE", "IDIOMA", "LINGUA"),
    "ui.revelation": ("REVELACIÓN", "REVELATION", "RÉVÉLATION", "REVELAÇÃO", "RIVELAZIONE"),
    "ui.seal_breathes": (
        "EL SELLO AÚN RESPIRA", "THE SEAL STILL BREATHES", "LE SCEAU RESPIRE ENCORE",
        "O SELO AINDA RESPIRA", "IL SIGILLO RESPIRA ANCORA"),
    "ui.hint": (
        "A/D MOVER · ESPACIO SALTAR · J GOLPEAR · K ESQUIVA · L LA VOZ",
        "A/D MOVE · SPACE JUMP · J STRIKE · K DODGE · L THE VOICE",
        "A/D BOUGER · ESPACE SAUTER · J FRAPPER · K ESQUIVER · L LA VOIX",
        "A/D MOVER · ESPAÇO SALTAR · J GOLPEAR · K ESQUIVAR · L A VOZ",
        "A/D MUOVI · SPAZIO SALTA · J COLPO · K SCHIVA · L LA VOCE"),
    "ui.ctrl_move": ("A / D          MOVERSE", "A / D          MOVE", "A / D          BOUGER",
                     "A / D          MOVER", "A / D          MUOVERSI"),
    "ui.ctrl_jump": ("ESPACIO        SALTAR", "SPACE          JUMP", "ESPACE         SAUTER",
                     "ESPAÇO         SALTAR", "SPAZIO         SALTARE"),
    "ui.ctrl_attack": ("J              GOLPEAR (COMBO DE 3)", "J              STRIKE (3-HIT COMBO)",
                       "J              FRAPPER (COMBO DE 3)", "J              GOLPEAR (COMBO DE 3)",
                       "J              COLPO (COMBO DA 3)"),
    "ui.ctrl_dash": ("K              ESQUIVA (INVULNERABLE)", "K              DODGE (INVULNERABLE)",
                     "K              ESQUIVER (INVULNÉRABLE)", "K              ESQUIVAR (INVULNERÁVEL)",
                     "K              SCHIVARE (INVULNERABILE)"),
    "ui.ctrl_voice": ("L              LA VOZ (CUESTA CORDURA)", "L              THE VOICE (COSTS SANITY)",
                      "L              LA VOIX (COÛTE LA RAISON)", "L              A VOZ (CUSTA SANIDADE)",
                      "L              LA VOCE (COSTA RAGIONE)"),
    "ui.ctrl_pause": ("ESC            PAUSA", "ESC            PAUSE", "ÉCHAP          PAUSE",
                      "ESC            PAUSA", "ESC            PAUSA"),
    "ui.resume": (
        "ESC PARA SEGUIR DESCENDIENDO", "ESC TO KEEP DESCENDING",
        "ÉCHAP POUR CONTINUER À DESCENDRE", "ESC PARA CONTINUAR A DESCER",
        "ESC PER CONTINUARE A SCENDERE"),

    # ----------------------------------------------------------------- muerte
    "death.title": (
        "LA MAREA TE DEVUELVE", "THE TIDE RETURNS YOU", "LA MARÉE TE REND",
        "A MARÉ DEVOLVE-TE", "LA MAREA TI RESTITUISCE"),
    "death.madness": ("LOCURA", "MADNESS", "FOLIE", "LOUCURA", "FOLLIA"),
    "death.deaths": ("MUERTES", "DEATHS", "MORTS", "MORTES", "MORTI"),

    # ----------------------------------------------------------------- final
    "end.title": (
        "EL SÉPTIMO SELLO", "THE SEVENTH SEAL", "LE SEPTIÈME SCEAU",
        "O SÉTIMO SELO", "IL SETTIMO SIGILLO"),
    "end.prompt": (
        "ENTER · REGRESO AL PRINCIPIO", "ENTER · BACK TO THE BEGINNING",
        "ENTRÉE · RETOUR AU COMMENCEMENT", "ENTER · VOLTAR AO INÍCIO",
        "INVIO · RITORNO ALL'INIZIO"),
    "end.next": (
        "ENTER · DESCENDER", "ENTER · DESCEND", "ENTRÉE · DESCENDRE",
        "ENTER · DESCER", "INVIO · SCENDERE"),
    "end.body": (
        "Cthulhu abre un ojo.\n\nNo hay batalla. Solo el peso de ser visto.\n\n"
        "El Testigo se arrodilla y el farol se apaga.\nLa locura llega a 7 / 7.\n\n"
        "El mundo se pliega sobre sí mismo y vuelve a empezar.\nInnsmouth. Otra vez. La misma lluvia.\n\n"
        "El Testigo desciende de nuevo, con la locura intacta\ny la vaga sensación de haber escrito esto antes.",
        "Cthulhu opens one eye.\n\nThere is no battle. Only the weight of being seen.\n\n"
        "The Witness kneels and the lantern goes out.\nMadness reaches 7 / 7.\n\n"
        "The world folds into itself and begins again.\nInnsmouth. Again. The same rain.\n\n"
        "The Witness descends once more, madness intact,\nwith the vague feeling of having written this before.",
        "Cthulhu ouvre un œil.\n\nIl n'y a pas de bataille. Seulement le poids d'être vu.\n\n"
        "Le Témoin s'agenouille et la lanterne s'éteint.\nLa folie atteint 7 / 7.\n\n"
        "Le monde se replie sur lui-même et recommence.\nInnsmouth. Encore. La même pluie.\n\n"
        "Le Témoin descend de nouveau, la folie intacte,\navec le vague sentiment d'avoir déjà écrit ceci.",
        "Cthulhu abre um olho.\n\nNão há batalha. Só o peso de ser visto.\n\n"
        "A Testemunha ajoelha-se e a lanterna apaga-se.\nA loucura chega a 7 / 7.\n\n"
        "O mundo dobra-se sobre si mesmo e recomeça.\nInnsmouth. Outra vez. A mesma chuva.\n\n"
        "A Testemunha desce de novo, com a loucura intacta\ne a vaga sensação de já ter escrito isto antes.",
        "Cthulhu apre un occhio.\n\nNon c'è battaglia. Solo il peso di essere visto.\n\n"
        "Il Testimone si inginocchia e la lanterna si spegne.\nLa follia arriva a 7 / 7.\n\n"
        "Il mondo si piega su se stesso e ricomincia.\nInnsmouth. Di nuovo. La stessa pioggia.\n\n"
        "Il Testimone scende ancora, con la follia intatta\ne la vaga sensazione di aver già scritto questo."),
}

# ------------------------------------------------------------------ jefes
BOSSES = [
    ("EL SACERDOTE AHOGADO", "THE DROWNED PRIEST", "LE PRÊTRE NOYÉ",
     "O SACERDOTE AFOGADO", "IL SACERDOTE AFFOGATO"),
    ("LA MADRE DE BRANQUIAS", "THE GILLED MOTHER", "LA MÈRE BRANCHUE",
     "A MÃE DE BRÂNQUIAS", "LA MADRE BRANCHIATA"),
    ("EL BIBLIOTECARIO", "THE LIBRARIAN", "LE BIBLIOTHÉCAIRE",
     "O BIBLIOTECÁRIO", "IL BIBLIOTECARIO"),
    ("EL CAZADOR DE LA LUNA", "THE MOON HUNTER", "LE CHASSEUR DE LUNE",
     "O CAÇADOR DA LUA", "IL CACCIATORE DI LUNA"),
    ("EL INGENIERO MI-GO", "THE MI-GO ENGINEER", "L'INGÉNIEUR MI-GO",
     "O ENGENHEIRO MI-GO", "L'INGEGNERE MI-GO"),
    ("EL YO QUE NO FUI", "THE SELF I NEVER WAS", "LE MOI QUE JE NE FUS PAS",
     "O EU QUE NÃO FUI", "L'IO CHE NON FUI"),
    ("CTHULHU", "CTHULHU", "CTHULHU", "CTHULHU", "CTHULHU"),
]
for i, row in enumerate(BOSSES):
    E["boss.%d" % i] = row

# ------------------------------------------------------------- susurros
WHISPERS = [
    ("NO MIRES HACIA ARRIBA", "DO NOT LOOK UP", "NE LÈVE PAS LES YEUX",
     "NÃO OLHES PARA CIMA", "NON GUARDARE IN ALTO"),
    ("YA ESTUVISTE AQUÍ", "YOU HAVE BEEN HERE BEFORE", "TU ES DÉJÀ VENU",
     "JÁ ESTIVESTE AQUI", "SEI GIÀ STATO QUI"),
    ("EL SELLO ERA TU NOMBRE", "THE SEAL WAS YOUR NAME", "LE SCEAU ÉTAIT TON NOM",
     "O SELO ERA O TEU NOME", "IL SIGILLO ERA IL TUO NOME"),
    ("NOSOTROS TE ABRIMOS", "WE OPENED YOU", "NOUS T'AVONS OUVERT",
     "NÓS ABRIMOS-TE", "NOI TI ABBIAMO APERTO"),
    ("CUENTA LOS TENTÁCULOS", "COUNT THE TENTACLES", "COMPTE LES TENTACULES",
     "CONTA OS TENTÁCULOS", "CONTA I TENTACOLI"),
    ("TU FAROL NO ALUMBRA NADA", "YOUR LANTERN LIGHTS NOTHING", "TA LANTERNE N'ÉCLAIRE RIEN",
     "A TUA LANTERNA NÃO ILUMINA NADA", "LA TUA LANTERNA NON ILLUMINA NULLA"),
    ("EL AGUA RECUERDA", "THE WATER REMEMBERS", "L'EAU SE SOUVIENT",
     "A ÁGUA LEMBRA-SE", "L'ACQUA RICORDA"),
    ("DESPIERTA... DESPIERTA...", "WAKE UP... WAKE UP...", "RÉVEILLE-TOI... RÉVEILLE-TOI...",
     "ACORDA... ACORDA...", "SVEGLIATI... SVEGLIATI..."),
    ("NO ERES EL PRIMERO", "YOU ARE NOT THE FIRST", "TU N'ES PAS LE PREMIER",
     "NÃO ÉS O PRIMEIRO", "NON SEI IL PRIMO"),
    ("ELLA TE ESPERA ABAJO", "SHE WAITS BELOW", "ELLE T'ATTEND EN BAS",
     "ELA ESPERA-TE EM BAIXO", "LEI TI ASPETTA GIÙ"),
    ("¿OYES LA MAREA?", "DO YOU HEAR THE TIDE?", "ENTENDS-TU LA MARÉE ?",
     "OUVES A MARÉ?", "SENTI LA MAREA?"),
    ("DEJA DE DESCENDER", "STOP DESCENDING", "CESSE DE DESCENDRE",
     "PÁRA DE DESCER", "SMETTI DI SCENDERE"),
]
for i, row in enumerate(WHISPERS):
    E["whisper.%d" % i] = row

# ---------------------------------------------------------------- etapas
STAGES = [
    # costa
    (("LA COSTA AHOGADA", "THE DROWNED COAST", "LA CÔTE NOYÉE",
      "A COSTA AFOGADA", "LA COSTA AFFOGATA"),
     ("INNSMOUTH · MAREA BAJA", "INNSMOUTH · LOW TIDE", "INNSMOUTH · MARÉE BASSE",
      "INNSMOUTH · MARÉ BAIXA", "INNSMOUTH · BASSA MAREA"),
     ("La Orden vigilaba siete sellos.\nAlguien los está abriendo desde dentro.",
      "The Order kept seven seals.\nSomeone is opening them from within.",
      "L'Ordre veillait sur sept sceaux.\nQuelqu'un les ouvre de l'intérieur.",
      "A Ordem vigiava sete selos.\nAlguém os está a abrir por dentro.",
      "L'Ordine custodiva sette sigilli.\nQualcuno li sta aprendo dall'interno."),
     ("El primer sello no estaba en la costa.\nEstaba en tu pecho, y ya no estaba.",
      "The first seal was not on the coast.\nIt was in your chest, and it was gone.",
      "Le premier sceau n'était pas sur la côte.\nIl était dans ta poitrine, et il n'y était plus.",
      "O primeiro selo não estava na costa.\nEstava no teu peito, e já não estava lá.",
      "Il primo sigillo non era sulla costa.\nEra nel tuo petto, e non c'era più."),
     [("Los peces de Innsmouth llevaban rostros.\nYo no quise mirar, y aun así miré.",
       "The fish of Innsmouth wore faces.\nI did not want to look, and still I looked.",
       "Les poissons d'Innsmouth portaient des visages.\nJe ne voulais pas regarder, et j'ai regardé.",
       "Os peixes de Innsmouth tinham rostos.\nNão quis olhar, e mesmo assim olhei.",
       "I pesci di Innsmouth avevano volti.\nNon volevo guardare, e guardai lo stesso."),
      ("El farero escribió: «el agua sube aunque no llueva».\nSu farol sigue encendido.",
       "The keeper wrote: «the water rises though it does not rain».\nHis lamp still burns.",
       "Le gardien écrivit : « l'eau monte sans qu'il pleuve ».\nSa lampe brûle encore.",
       "O faroleiro escreveu: «a água sobe mesmo sem chuva».\nO farol dele ainda está aceso.",
       "Il guardiano scrisse: «l'acqua sale anche se non piove».\nLa sua lanterna brucia ancora."),
      ("En el registro de la aduana, el mismo barco\nzarpó siete veces el mismo día.",
       "In the customs ledger, the same ship\nsailed seven times on the same day.",
       "Dans le registre des douanes, le même navire\nappareilla sept fois le même jour.",
       "No registo da alfândega, o mesmo navio\npartiu sete vezes no mesmo dia.",
       "Nel registro della dogana, la stessa nave\nsalpò sette volte lo stesso giorno.")]),
    # criptas
    (("LAS CRIPTAS DE DAGON", "THE CRYPTS OF DAGON", "LES CRYPTES DE DAGON",
      "AS CRIPTAS DE DAGON", "LE CRIPTE DI DAGON"),
     ("BAJO INNSMOUTH · NIVEL -2", "BENEATH INNSMOUTH · LEVEL -2", "SOUS INNSMOUTH · NIVEAU -2",
      "SOB INNSMOUTH · NÍVEL -2", "SOTTO INNSMOUTH · LIVELLO -2"),
     ("Bajo el puerto, la piedra recuerda otra marea.",
      "Beneath the harbour, the stone remembers another tide.",
      "Sous le port, la pierre se souvient d'une autre marée.",
      "Debaixo do porto, a pedra lembra-se de outra maré.",
      "Sotto il porto, la pietra ricorda un'altra marea."),
     ("La escalera baja en espiral.\nLa has bajado antes. Los peldaños lo saben.",
      "The stair goes down in a spiral.\nYou have descended it before. The steps know.",
      "L'escalier descend en spirale.\nTu l'as déjà descendu. Les marches le savent.",
      "A escada desce em espiral.\nJá a desceste antes. Os degraus sabem.",
      "La scala scende a spirale.\nL'hai già discesa. I gradini lo sanno."),
     [("Dagon no es un dios. Es una etapa del camino.\nLos que llegan arriba lo entienden tarde.",
       "Dagon is not a god. He is a stage of the road.\nThose who reach the top learn it too late.",
       "Dagon n'est pas un dieu. C'est une étape du chemin.\nCeux qui arrivent en haut le comprennent trop tard.",
       "Dagon não é um deus. É uma etapa do caminho.\nQuem chega ao topo entende tarde demais.",
       "Dagon non è un dio. È una tappa del cammino.\nChi arriva in cima lo capisce troppo tardi."),
      ("Los sacerdotes se ataban lastres para no flotar.\nUno de ellos no necesitó lastre.",
       "The priests tied weights to themselves so they would not float.\nOne of them needed no weight.",
       "Les prêtres s'attachaient des poids pour ne pas flotter.\nL'un d'eux n'en eut pas besoin.",
       "Os sacerdotes amarravam pesos para não flutuar.\nUm deles não precisou de peso.",
       "I sacerdoti si legavano dei pesi per non galleggiare.\nUno di loro non ne ebbe bisogno."),
      ("Aquí se bautizaba dos veces: una con agua\ny otra con algo que respira dentro del agua.",
       "Here they baptised twice: once with water,\nand once with something that breathes inside the water.",
       "Ici on baptisait deux fois : une fois avec l'eau,\net une fois avec ce qui respire dans l'eau.",
       "Aqui batizavam duas vezes: uma com água\ne outra com algo que respira dentro da água.",
       "Qui si battezzava due volte: una con l'acqua\ne una con qualcosa che respira dentro l'acqua.")]),
    # biblioteca
    (("EL ALA PROHIBIDA", "THE FORBIDDEN WING", "L'AILE INTERDITE",
      "A ALA PROIBIDA", "L'ALA PROIBITA"),
     ("MISKATONIC · ARKHAM", "MISKATONIC · ARKHAM", "MISKATONIC · ARKHAM",
      "MISKATONIC · ARKHAM", "MISKATONIC · ARKHAM"),
     ("Hay libros que no se leen. Se escuchan.",
      "Some books are not read. They are heard.",
      "Il est des livres qu'on ne lit pas. On les écoute.",
      "Há livros que não se leem. Ouvem-se.",
      "Ci sono libri che non si leggono. Si ascoltano."),
     ("Comprendiste una palabra que no existe.\nDesde ese momento, el mundo tiene una grieta.",
      "You understood a word that does not exist.\nFrom that moment, the world has a crack.",
      "Tu as compris un mot qui n'existe pas.\nDepuis, le monde a une fissure.",
      "Compreendeste uma palavra que não existe.\nDesde esse momento, o mundo tem uma fenda.",
      "Hai compreso una parola che non esiste.\nDa quel momento, il mondo ha una crepa."),
     [("El Necronomicón no me leía a mí.\nMe estaba traduciendo a mí.",
       "The Necronomicon was not reading me.\nIt was translating me.",
       "Le Necronomicon ne me lisait pas.\nIl me traduisait.",
       "O Necronomicon não me estava a ler.\nEstava a traduzir-me.",
       "Il Necronomicon non mi stava leggendo.\nMi stava traducendo."),
      ("Alguien anotó al margen: «no es un texto,\nes una puerta con índice».",
       "Someone wrote in the margin: «this is not a text,\nit is a door with an index».",
       "Quelqu'un nota en marge : « ce n'est pas un texte,\nc'est une porte avec un index ».",
       "Alguém anotou à margem: «não é um texto,\né uma porta com índice».",
       "Qualcuno annotò a margine: «non è un testo,\nè una porta con l'indice»."),
      ("El bibliotecario lleva 40 años ordenando\nel mismo estante. El estante ya no está.",
       "The librarian has spent 40 years sorting\nthe same shelf. The shelf is gone.",
       "Le bibliothécaire range le même rayon depuis 40 ans.\nLe rayon n'est plus là.",
       "O bibliotecário passa 40 anos a arrumar\na mesma estante. A estante já não está lá.",
       "Il bibliotecario passa 40 anni a ordinare\nlo stesso scaffale. Lo scaffale non c'è più.")]),
    # meseta
    (("LA MESETA DE LENG", "THE PLATEAU OF LENG", "LE PLATEAU DE LENG",
      "O PLATÔ DE LENG", "L'ALTOPIANO DI LENG"),
     ("KADATH · LUNA LLENA", "KADATH · FULL MOON", "KADATH · PLEINE LUNE",
      "KADATH · LUA CHEIA", "KADATH · LUNA PIENA"),
     ("El frío no viene del hielo. Viene de arriba.",
      "The cold does not come from the ice. It comes from above.",
      "Le froid ne vient pas de la glace. Il vient d'en haut.",
      "O frio não vem do gelo. Vem de cima.",
      "Il freddo non viene dal ghiaccio. Viene da sopra."),
     ("El cielo no es un techo.\nEs un párpado a medio cerrar.",
      "The sky is not a ceiling.\nIt is an eyelid, half closed.",
      "Le ciel n'est pas un plafond.\nC'est une paupière à demi fermée.",
      "O céu não é um teto.\nÉ uma pálpebra meio fechada.",
      "Il cielo non è un soffitto.\nÈ una palpebra socchiusa."),
     [("No había cima. Solo un ojo abierto\ny la certeza de estar siendo leído.",
       "There was no summit. Only an open eye\nand the certainty of being read.",
       "Il n'y avait pas de sommet. Seulement un œil ouvert\net la certitude d'être lu.",
       "Não havia cume. Só um olho aberto\ne a certeza de estar a ser lido.",
       "Non c'era vetta. Solo un occhio aperto\ne la certezza di essere letto."),
      ("Los cazadores de Leng no matan por hambre.\nCazan para que algo los mire.",
       "The hunters of Leng do not kill from hunger.\nThey hunt so that something will watch them.",
       "Les chasseurs de Leng ne tuent pas de faim.\nIls chassent pour qu'on les regarde.",
       "Os caçadores de Leng não matam por fome.\nCaçam para que algo os olhe.",
       "I cacciatori di Leng non uccidono per fame.\nCacciano perché qualcosa li guardi."),
      ("La luna tiene una boca. No se ve\ndesde abajo. Se ve desde dentro.",
       "The moon has a mouth. You cannot see it\nfrom below. You see it from inside.",
       "La lune a une bouche. On ne la voit pas\nd'en bas. On la voit de l'intérieur.",
       "A lua tem uma boca. Não se vê\nde baixo. Vê-se de dentro.",
       "La luna ha una bocca. Non si vede\nda sotto. Si vede da dentro.")]),
    # yuggoth
    (("EL ABISMO DE YUGGOTH", "THE ABYSS OF YUGGOTH", "L'ABÎME DE YUGGOTH",
      "O ABISMO DE YUGGOTH", "L'ABISSO DI YUGGOTH"),
     ("CIUDAD-MÁQUINA · ÓRBITA EXTERIOR", "MACHINE-CITY · OUTER ORBIT",
      "CITÉ-MACHINE · ORBITE EXTERNE", "CIDADE-MÁQUINA · ÓRBITA EXTERNA",
      "CITTÀ-MACCHINA · ORBITA ESTERNA"),
     ("Aquí los cerebros se guardan en tarros.\nY aun así sienten miedo.",
      "Here brains are kept in jars.\nAnd still they feel fear.",
      "Ici, les cerveaux sont gardés dans des bocaux.\nEt ils ont encore peur.",
      "Aqui os cérebros guardam-se em frascos.\nE mesmo assim sentem medo.",
      "Qui i cervelli si conservano in barattoli.\nE provano ancora paura."),
     ("No estás descendiendo.\nEstás subiendo por dentro de un cuerpo.",
      "You are not descending.\nYou are climbing inside a body.",
      "Tu ne descends pas.\nTu montes à l'intérieur d'un corps.",
      "Não estás a descer.\nEstás a subir por dentro de um corpo.",
      "Non stai scendendo.\nStai salendo dentro un corpo."),
     [("Mi cerebro estaba en un tarro y aun así\nsentía miedo. Eso fue lo más humano que recuerdo.",
       "My brain was in a jar and still\nit felt fear. That was the most human thing I remember.",
       "Mon cerveau était dans un bocal et il avait\nencore peur. C'est le plus humain dont je me souvienne.",
       "O meu cérebro estava num frasco e mesmo assim\nsentia medo. Foi a coisa mais humana de que me lembro.",
       "Il mio cervello era in un barattolo e provava\nancora paura. È la cosa più umana che ricordo."),
      ("Los Mi-Go no tienen dioses. Tienen\nproveedores, y nosotros somos el pedido.",
       "The Mi-Go have no gods. They have\nsuppliers, and we are the order.",
       "Les Mi-Go n'ont pas de dieux. Ils ont\ndes fournisseurs, et nous sommes la commande.",
       "Os Mi-Go não têm deuses. Têm\nfornecedores, e nós somos a encomenda.",
       "I Mi-Go non hanno dèi. Hanno\nfornitori, e noi siamo l'ordine."),
      ("La máquina canta en siete tiempos.\nUno de esos tiempos es tu nombre.",
       "The machine sings in seven times.\nOne of those times is your name.",
       "La machine chante en sept temps.\nL'un de ces temps est ton nom.",
       "A máquina canta em sete tempos.\nUm desses tempos é o teu nome.",
       "La macchina canta in sette tempi.\nUno di quei tempi è il tuo nome.")]),
    # rlyeh
    (("EL SUEÑO DE R'LYEH", "THE DREAM OF R'LYEH", "LE RÊVE DE R'LYEH",
      "O SONHO DE R'LYEH", "IL SOGNO DI R'LYEH"),
     ("CIUDAD NO EUCLIDIANA · SIN SUPERFICIE", "NON-EUCLIDEAN CITY · NO SURFACE",
      "CITÉ NON-EUCLIDIENNE · SANS SURFACE", "CIDADE NÃO EUCLIDIANA · SEM SUPERFÍCIE",
      "CITTÀ NON EUCLIDEA · SENZA SUPERFICIE"),
     ("No hay arriba. No hay abajo.\nSolo ángulos que no debían juntarse.",
      "There is no above. There is no below.\nOnly angles that should not meet.",
      "Il n'y a pas d'en haut. Il n'y a pas d'en bas.\nSeulement des angles qui ne devaient pas se joindre.",
      "Não há cima. Não há baixo.\nSó ângulos que não deviam juntar-se.",
      "Non c'è sopra. Non c'è sotto.\nSolo angoli che non dovevano incontrarsi."),
     ("El sexto sello era una persona.\nLa reconociste por la espalda, como siempre.",
      "The sixth seal was a person.\nYou knew them from behind, as always.",
      "Le sixième sceau était une personne.\nTu l'as reconnue de dos, comme toujours.",
      "O sexto selo era uma pessoa.\nReconheceste-a de costas, como sempre.",
      "Il sesto sigillo era una persona.\nL'hai riconosciuta di spalle, come sempre."),
     [("Me vi en un espejo de agua.\nMe reconocí. Él no.",
       "I saw myself in a mirror of water.\nI recognised myself. He did not.",
       "Je me suis vu dans un miroir d'eau.\nJe me suis reconnu. Lui, non.",
       "Vi-me num espelho de água.\nReconheci-me. Ele não.",
       "Mi sono visto in uno specchio d'acqua.\nMi sono riconosciuto. Lui no."),
      ("Aquí las paredes son el mismo pasillo\nvisto desde siete sitios a la vez.",
       "Here the walls are the same corridor\nseen from seven places at once.",
       "Ici les murs sont le même couloir\nvu de sept endroits à la fois.",
       "Aqui as paredes são o mesmo corredor\nvisto de sete sítios ao mesmo tempo.",
       "Qui le pareti sono lo stesso corridoio\nvisto da sette punti insieme."),
      ("Encontré mi letra en un muro.\nDecía: «no cruces el séptimo».",
       "I found my own handwriting on a wall.\nIt said: «do not cross the seventh».",
       "J'ai trouvé mon écriture sur un mur.\nElle disait : « ne franchis pas le septième ».",
       "Encontrei a minha letra numa parede.\nDizia: «não atravesses o sétimo».",
       "Ho trovato la mia scrittura su un muro.\nDiceva: «non attraversare il settimo».")]),
    # trono
    (("EL TRONO DEL DURMIENTE", "THE THRONE OF THE SLEEPER", "LE TRÔNE DU DORMEUR",
      "O TRONO DO ADORMECIDO", "IL TRONO DEL DORMIENTE"),
     ("R'LYEH · LA CÁMARA DEL SUEÑO", "R'LYEH · THE DREAMING CHAMBER", "R'LYEH · LA CHAMBRE DU RÊVE",
      "R'LYEH · A CÂMARA DO SONHO", "R'LYEH · LA CAMERA DEL SOGNO"),
     ("El que sueña no duerme.\nSueña con quien baja.",
      "The one who dreams is not asleep.\nHe dreams of whoever descends.",
      "Celui qui rêve ne dort pas.\nIl rêve de celui qui descend.",
      "O que sonha não dorme.\nSonha com quem desce.",
      "Chi sogna non dorme.\nSogna chi scende."),
     ("Lo rompiste tú. En otra vuelta.\nY has estado descendiendo la misma escalera durante siglos.",
      "You broke it. In another turn.\nAnd you have descended the same stair for centuries.",
      "C'est toi qui l'as brisé. À un autre tour.\nEt tu descends le même escalier depuis des siècles.",
      "Foste tu que o rompeste. Noutra volta.\nE desces a mesma escada há séculos.",
      "L'hai spezzato tu. In un altro giro.\nE scendi la stessa scala da secoli."),
     [("Los siete sellos no eran puertas.\nEran los dedos de una mano cerrada.",
       "The seven seals were not doors.\nThey were the fingers of a closed hand.",
       "Les sept sceaux n'étaient pas des portes.\nC'étaient les doigts d'une main fermée.",
       "Os sete selos não eram portas.\nEram os dedos de uma mão fechada.",
       "I sette sigilli non erano porte.\nErano le dita di una mano chiusa."),
      ("El culto no lo despertó.\nSolo le apartó el pelo de los ojos.",
       "The cult did not wake him.\nThey only brushed the hair from his eyes.",
       "Le culte ne l'a pas réveillé.\nIl lui a seulement écarté les cheveux des yeux.",
       "O culto não o acordou.\nSó lhe afastou o cabelo dos olhos.",
       "Il culto non lo ha svegliato.\nGli ha solo spostato i capelli dagli occhi."),
      ("Yo soy el séptimo sello.\nSiempre lo fui.",
       "I am the seventh seal.\nI always was.",
       "Je suis le septième sceau.\nJe l'ai toujours été.",
       "Eu sou o sétimo selo.\nSempre fui.",
       "Io sono il settimo sigillo.\nLo sono sempre stato.")]),
]

STAGE_KEYS = ["costa", "criptas", "biblioteca", "meseta", "yuggoth", "rlyeh", "trono"]

for key, row in zip(STAGE_KEYS, STAGES):
    name, subtitle, intro, rev, frags = row
    E["stage.%s.name" % key] = name
    E["stage.%s.subtitle" % key] = subtitle
    E["stage.%s.intro" % key] = intro
    E["stage.%s.revelation" % key] = rev
    for i, f in enumerate(frags):
        E["stage.%s.frag.%d" % (key, i)] = f


def build() -> dict:
    out = {lang: {} for lang in LANGS}
    missing = []
    for key, values in E.items():
        if len(values) != len(LANGS):
            missing.append(key)
            continue
        for lang, text in zip(LANGS, values):
            out[lang][key] = text
    if missing:
        raise SystemExit("claves con nº de traducciones incorrecto: %s" % missing)
    # comprobar que ninguna lengua queda coja
    for lang in LANGS:
        faltan = [k for k in E if k not in out[lang]]
        if faltan:
            raise SystemExit("%s: faltan %d claves" % (lang, len(faltan)))
    return out


def main(outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    data = build()
    for lang in LANGS:
        payload = {"_name": NAMES[lang], "_code": lang, "strings": data[lang]}
        path = os.path.join(outdir, "%s.json" % lang)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print("%s: %d cadenas" % (lang, len(data[lang])))
    index = {"languages": [{"code": l, "name": NAMES[l]} for l in LANGS], "default": "es"}
    with open(os.path.join(outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("total claves:", len(E))


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "lang")
    main(root)
