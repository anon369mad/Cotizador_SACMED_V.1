import os#Sirve para  interactuar con el sistema operativo, en este caso para obtener variables de entorno
from sqlalchemy import create_engine#crea una conexión a la base de datos
from sqlalchemy.orm import sessionmaker#gestiona las sesiones de la base de datos
from dotenv import load_dotenv#carga variables de entorno desde un archivo .env

load_dotenv()#carga las variables de entorno desde un archivo .env, osea busca un archivo llamado .env en el directorio actual y carga las variables definidas allí en el entorno de ejecución de Python.

DB_HOST = os.getenv("DB_HOST")#Busca y obtiene el valor de la variable de entorno DB_HOST, guardada en el archivo .env
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)#crea una cadena 
#con el formato necesario para que SQLAlchemy 
# pueda conectarse a la base de datos MySQL utilizando el conector pymysql.
#(pymysql es un conector de MySQL para Python 
# que permite a las aplicaciones Python interactuar con bases de datos MySQL. Es el driver que SQLAlchemy utilizará para conectarse a MySQL en este caso.)

engine = create_engine(DATABASE_URL, echo=True)
#Aqui se toma la cadena de conexión DATABASE_URL y se crea un motor de base de datos utilizando SQLAlchemy.
#El motor es el componente que maneja la conexión a la base de datos y ejecuta las consultas.
#Con la url sabe a qué base de datos conectarse y cómo hacerlo.
#El parámetro echo=True habilita el registro de todas las sentencias SQL generadas por SQLAlchemy, lo que es útil para depuración.
#el registro se imprime en la consola o en el log de la aplicación.
#En engine se almacena el motor de base de datos creado.

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)#sessionmaker es una fábrica de sesiones que crea nuevas instancias de sesión de base de datos.
#autocommit=False significa que las transacciones no se confirmarán automáticamente después de cada operación
#autoflush=False significa que los cambios realizados en la sesión no se enviarán automáticamente a la base de datos antes de ciertas operaciones.
#bind=engine vincula las sesiones creadas por esta fábrica al motor de base de datos creado anteriormente.

#En resumen, este archivo configura la conexión a una base de datos MySQL utilizando SQLAlchemy.
#SQLAlchemy es una biblioteca ORM (Object-Relational Mapping) para Python que facilita la interacción con bases de datos relacionales.
#mas especificamente:
#- Se importa la librería os para manejar variables de entorno.
#- Se importa create_engine y sessionmaker de SQLAlchemy para manejar la conexión y sesiones de
#  base de datos.
#- Se importa load_dotenv de python-dotenv para cargar variables de entorno desde un archivo
#- Se cargan las variables de entorno desde el archivo .env
#- Se obtienen las variables necesarias para la conexión a la base de datos (host,
#  puerto, nombre, usuario, contraseña).
#- Se construye la URL de conexión a la base de datos MySQL.
#- Se crea el motor de base de datos con create_engine usando la URL y se activa el registro de SQL.
#- Se crea una fábrica de sesiones con sessionmaker vinculada al motor creado
