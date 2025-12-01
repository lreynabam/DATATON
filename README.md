# DATATON 2025
# EQUIPO: CAZADORES DE PATRONES ATÍPICOS:
# Prototipo de Sistema de Análisis de Evolución Patrimonial de Servidores Públicos
Este proyecto es un sistema para hacer un análisis de las declaraciones patrimoniales y fiscales de los servidores públicos. El sistema hace uso de archivos JSON con los datos correspondientes a cada uno, tomando en cuenta la suma de sus activos y pasivos acumulado en el periodo de tiempo correspondiente. La identificación de anomalías se lleva a cabo por medio de un modelo de aprendizaje automático o machine learning entrenado, para fines prácticos, a partir de cinco archivos JSON de estados de la república mexicana y una organización, por lo cual se recomienda ampliar la cantidad de archivos para lograr una mejor detección. El algoritmo utilizado es Isolation Forest con los siguientes criterios:
Estimación de árboles: 200
Contaminación de datos 0.02
Reproducibilidad: 42.

El objetivo principal es apoyar en la detección temprana de casos atípicos que requieran una revisión más profunda de ello. 

# Funcionalidades
El sistema permite la carga de archivos JSON.
Se extraen los campos clave y banderas
Se transforman los datos a un DataFrame estructurado para análisis. 
Se ejecuta el modelo entrenado y se clasifica en anómalo o normal según un puntaje:
Score > 0 = Normal 
Score < 0 = Atípico 
Muestra del resultado en un DataTable dentro de la interfaz web
Opción de descarga en un archivo JSON para su análisis. 

# Entrenamiento del modelo
El proceso de entrenamiento puede verse observado en el archivo logicaModelo, así como en el archivo Datatonv2.2.ipnyb

Para correr el sistema con la interfaz web en un servidor local, puede realizarse desde consola creando un entorno virtual dentro de la carpeta del proyecto con:
    python -m venv venv
y activarlo con:
    .\venv\Scripts\Activate.ps1
Posterior a la instalación de las dependencias especificadas en requirements.txt, se ejecuta el archivo app.py de la siguiente manera:
   python app.py
Si se desea acceder desde internet, visita el siguiente sitio: 
https://luisaayon25.pythonanywhere.com/