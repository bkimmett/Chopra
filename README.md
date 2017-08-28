# Chopra

Chopra is my port of ScireSM's Pokémon Shuffle Unpacker (https://github.com/SciresM/Pokemon-Shuffle-Unpacker). It's written in Python, so anyone can use it.

## Usage

**Unpack a file:**
`./depack.py file_to_unpack`

**Unpack a folder:**
`./depack.py folder_to_unpack`
(Any subdirectories of the folder will be ignored.)

Chopra is expecting files dumped from 3DS Extra Data; it performs certain magic number checks to verify this, so any other random file it is given will be ignored. If you think something should be unpacked but is not, please open an issue.