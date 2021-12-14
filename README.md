# Bot citas Registro Civil para gva.es

Para utilizar este bot, se requiere de una versión Python 3.6 o superior.

# Instalación

```bash
pip3 install -r requirements.txt
```

# Uso
La descripción de todos los parámetros se puede obtener ejecutando:
```
$ python cita_gva.py --help
usage: cita_gva.py [-h] [-v] [-p [PROVINCIA]] [-m [MUNICIPIO]] [-s [SERVICIO]]
                   -d DNI -n NOMBRE -a1 APELLIDO1 [-a2 APELLIDO2] -f FECHA
                   [-x CITAMIN] [-y CITAMAX] [-z HORAOBJETIVO] -o OUTPUT
                   [-w WAIT]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Incrementa la verbosidad (default: 3)

Obligatorios:
  -p [PROVINCIA], --provincia [PROVINCIA]
                        Nombre de provincia. Vacío para consultar valores
                        posibles (default: None)
  -m [MUNICIPIO], --municipio [MUNICIPIO]
                        Nombre de municipio. Vacío para consultar valores
                        posibles (default: None)
  -s [SERVICIO], --servicio [SERVICIO]
                        Motivo de la cita. Vacío para consultar valores
                        posibles (default: None)
  -d DNI, --dni DNI     DNI/NIE (default: None)
  -n NOMBRE, --nombre NOMBRE
                        Nombre (default: None)
  -a1 APELLIDO1, --apellido1 APELLIDO1
                        Primer apellido (default: None)
  -f FECHA, --fecha FECHA
                        Fecha de nacimiento (dd/mm/YYYY) (default: None)
  -o OUTPUT, --output OUTPUT
                        fichero PDF de la cita confirmada (default: None)

Opcionales:
  -a2 APELLIDO2, --apellido2 APELLIDO2
                        Segundo apellido (default: None)
  -x CITAMIN, --citamin CITAMIN
                        Fecha mínima de la cita (dd/mm/YYYY). Citas anteriores
                        a dicha fecha serán ignoradas (default: 2021-12-14
                        01:30:38.810895)
  -y CITAMAX, --citamax CITAMAX
                        Fecha máxima de la cita (dd/mm/YYYY). Citas
                        posteriores a dicha fecha serán ignoradas (default:
                        None)
  -z HORAOBJETIVO, --horaobjetivo HORAOBJETIVO
                        Hora cita (HH:MM). Se usará como preferencia para
                        escoger en caso de haber más de una cita disponible
                        (default: None)
  -w WAIT, --wait WAIT  Tiempo de espera entre solicitudes (default: 30)
```

Los parámetros mínimos son:

- -d  - DNI
- -n  - Nombre
- -a1 - Primer apellido
- -f  - Fecha de nacimiento
- -o  - Fichero PDF de salida

Los parámetros `-p` `-m` `-s` son obligatorios. Si no se especifican, se mostrará una ayuda de los posibles valores y se terminará la ejecución con un error. Ejemplo:

```
python cita_gva.py -d X1234567A -n Sancho -a1 Panza -f 16/02/1955 -o fichero.pdf -p Valencia -m Valencia
2021-12-12 11:26:51 - CRITICAL: Error de argumento "SERVICIO". Valores posibles:
2021-12-12 11:26:51 - CRITICAL: SOLICITUD DE CERTIFICADO DE DEFUNCION
2021-12-12 11:26:51 - CRITICAL: SOLICITUD CERTIFICADO DE MATRIMONIO
2021-12-12 11:26:51 - CRITICAL: SOLICITUD CERTIFICADO DE NACIMIENTO
2021-12-12 11:26:51 - CRITICAL: EXPEDIENTE DE CAMBIO DE NOMBRE/RECTIFICACION REGISTRAL DEL SEXO
2021-12-12 11:26:51 - CRITICAL: EXPEDIENTE DE MATRIMONIO
2021-12-12 11:26:51 - CRITICAL: SOLICITUD FE DE VIDA Y ESTADO
2021-12-12 11:26:51 - CRITICAL: INSCRIPCION DE MATRIMONIO CANONICO
2021-12-12 11:26:51 - CRITICAL: INSCRIPCION DE NACIMIENTO FUERA DE PLAZO
2021-12-12 11:26:51 - CRITICAL: INSCRIPCION DE RECIÉN NACIDO
2021-12-12 11:26:51 - CRITICAL: JURAMENTO EXPEDIENTE DE NACIONALIDAD
2021-12-12 11:26:51 - CRITICAL: OTROS TRAMITES DE MATRIMONIO (CAPITULACIONES, TRASLADOS...)
2021-12-12 11:26:51 - CRITICAL: OTROS TRAMITES DE NACIONALIDAD
2021-12-12 11:26:51 - CRITICAL: OTROS TRAMITES DE NACIMIENTO Y DEFUNCION
2021-12-12 11:26:51 - CRITICAL: SIMPLE PRESUNCIÓN (NACIONALIDAD)
```

En este caso, nos falta especificar el parámetro `-s` (Servicio), el cual puede ser únicamente las primeras palabras del procedimiento. Por ejemplo: `python cita_gva.py ..... -s simple`