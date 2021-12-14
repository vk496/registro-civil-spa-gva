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