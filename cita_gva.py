import io
from json.decoder import JSONDecodeError
import speech_recognition as sr
import requests
import urllib.parse
from lxml import html
import re
import time
import wave
import json
import datetime
import logging
import argparse
import sys
from strenum import StrEnum

# Reuse connections
client = requests.Session()


# https://www.tramita.gva.es/ctt-att-atr/asistente/iniciarTramite.html?tramite=CITA_PREVIA&version=2&idioma=es&idProcGuc=14104&idCatGuc=PR


class APIconst(StrEnum):
    PROVINCIA = 'SOL_PROV'
    MUNICIPIO = 'SOL_MUNI'
    SERVICIO = 'SOL_SERVICIO'
    NOMBRE = 'SOL_NOMBRE'
    DNI = 'SOL_DNI'
    APELLIDO1 = 'SOL_APELLIDO1'
    APELLIDO2 = 'SOL_APELLIDO2'
    FECHA = 'SOL_FECHA'
    CENTRO = 'SOL_CENTRO'


class OldDateError(ValueError):
    pass


class APIobject:
    def __init__(self, structure_template):
        logging.debug("APIobject: Plantilla inicial - %s", structure_template)
        self._initial_template = structure_template
        self._values = {}
        self._fill_values_(structure_template)

    def _fill_values_(self, template):
        logging.debug("APIobject: Nueva plantilla - %s", template)
        self._template = template
        # Replace existing values
        for v in self._template['datos']['valores']:
            logging.debug("APIobject: id %s con valor %s", v['id'], v)
            id = v['id']
            self._values[id] = v
            if v['valor']:
                logging.debug('%s = %s', id, v['valor'])

        # Replace values if they are unique possible
        for v in self._template['datos']['valoresPosibles']:
            logging.debug("APIobject: id %s con valorPosible %s", v['id'], v)
            if v['valores'] != None and len(v['valores']) == 1:
                logging.debug(
                    "APIobject: valorPosible %s solo tiene un candidato: %s", v['id'], v)
                self.fillValor(v['id'], v['valores'][0]['descripcion'])
    """
    Function that fills data with the suggestion from the template (using descripcion attribute as reference to search)
    When calling this function, it may replace other values than id, since it calls the API server to validate
    """

    def fillValor(self, id, text_like):
        logging.debug(
            "APIobject: Rellenar %s con valor del tipo %s", id, text_like)
        if id not in self._values:
            raise KeyError("Id " + id +
                           " was not previously defined in the template")

        logging.debug("APIobject: valoresPosibles: %s",
                      self._template['datos']['valoresPosibles'])
        for possibleValues in self._template['datos']['valoresPosibles']:
            if possibleValues['id'] == id:
                for v in possibleValues['valores']:
                    if text_like.lower() in v['descripcion'].lower():
                        logging.debug(
                            "APIobject: id %s fijado a valor %s", id, v)
                        self._values[id]['valor'] = v

                        logging.debug("APIobject: Validar desde el servidor")
                        validar = template_request(
                            "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/evaluarCambioCampo.html",
                            verb='POST',
                            validate_API=True,
                            extraHeaders={
                                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                "X-CSRF-Token": tokenCSRF,
                                "X-Requested-With": "XMLHttpRequest"
                            },
                            data=self.dumps(extra_att={'idCampo': id})
                        )

                        # Inform user about which values are used
                        logging.debug('%s = %s', id, v['descripcion'])

                        logging.debug(
                            "APIobject: Servidor responde con plantilla")
                        self._fill_values_(validar.json())
                        return self
        # raise ValueError("Id " + id + " no tiene un valor del tipo %s" + text_like)
        logging.fatal(
            'Id "%s" no tiene un valor del tipo "%s". Valores posibles:', id, text_like)
        try:
            for v in self._template['datos']['valoresPosibles']:
                if v['id'] == id:
                    for vl in v['valores']:
                        logging.fatal(vl['descripcion'])
                    break
        except Exception:
            pass
        sys.exit(1)

    """
    addValor add a value to a already existing structure. No validation is made
    """

    def addValor(self, id, value):
        logging.debug("APIobject: addValor Id %s con %s", id, value)
        self._values[id]['valor'] = value
        logging.debug('%s = %s', id, value)
        return self

    def getDescripcion(self, id):
        return self._values[id]['valor']['descripcion']

    def getPossibleValue(self, id):
        logging.debug("APIobject: getPossibleValue Id %s dentro de ",
                      id, self._initial_template['datos']['valoresPosibles'])

        # Primero intentamos la última template. Si no, la inicial
        for t in ['_template', '_initial_template']:
            for possibleValues in self.__dict__[t]['datos']['valoresPosibles']:
                if possibleValues['id'] == id:
                    return possibleValues['valores']
        raise KeyError("No valoresPosibles for " + id)

    def setCaptcha(self, captcha):
        logging.debug("APIobject: Establecer captcha a %s", captcha)
        self._addValor('B_TEXTO_CAPTCHA', 's', str(captcha))

    def _addValor(self, id, tipo, valor):
        logging.debug(
            "APIobject: Crear %s del tipo %s con valor %s", id, tipo, valor)
        self._values[id] = {
            'id': id,
            'tipo': tipo,
            'valor': valor,
        }

    def dumps(self, extra_att={}, as_json=False):
        export = ""
        for k, v in self._values.items():
            export += '&' + k + "=" + json.dumps(v)
        for k, v in extra_att.items():
            export += '&' + k + '=' + str(v)
        export = export[1:]  # Remove first &
        logging.debug("APIobject: exportar como: %s", export)
        if not as_json:
            export = urllib.parse.quote_plus(export, safe='&=()')
            logging.debug("APIobject: exportar bruto: %s", export)
        return export


def template_request(url, verb='GET', extraHeaders={}, validate_API=False, data=None):
    basic_headers = {
        "Accept": "*/*; q=0.01",
        "Connection": "keep-alive",
        "Origin": "https://www.tramita.gva.es",
        "Referer": "https://www.tramita.gva.es/ctt-att-atr/asistente/asistente.html",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
    }

    finalHeaders = {**basic_headers, **extraHeaders}

    logging.debug('Peticion %s a url "%s" con cabeceras %s y datos %s',
                  verb, url, finalHeaders, data)
    req = client.request(verb, url,
                         headers=finalHeaders, data=data)

    try:
        myresp = req.json()
    except JSONDecodeError:
        if validate_API:
            raise RuntimeError(req)

    if not req.ok or (validate_API and (myresp['estado'] != 'SUCCESS')):
        if not req.ok:
            raise RuntimeError(req.status_code + ": " + req.content)

        raise RuntimeError("Error API: " + str(myresp))

    if validate_API:
        if 'datos' in myresp and myresp['datos'] != None:
            if 'validacion' in myresp['datos'] and myresp['datos']['validacion'] != None:
                if myresp['datos']['validacion']['estado'] == 'error':
                    newdate = re.search("[Ll]a fecha no puede ser inferior a la del d[íi]a de hoy (\d\d/\d\d/\d\d\d\d)",
                                        myresp['datos']['validacion']['mensaje'])
                    if newdate:
                        raise OldDateError(newdate.group(1))

    return req


def do_process(op):
    logging.debug("Informacion tramite")
    template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/informacionTramite.html",
        verb='POST',
        validate_API=True,
        extraHeaders={
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )

    logging.debug("ir a Paso")
    template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/irAPaso.html",
        verb='POST',
        data='id=' + op,
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )

    logging.debug("Abrir formulario")
    formTicket = template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/capturar/abrirFormulario.html",
        verb='POST',
        data='idPaso='+op+'&id=' + op,
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )

    logging.debug("Cargar formulario")
    template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/cargarFormulario.html",
        verb='POST',
        data='idPaso='+op+'&id='+op+'&ticket=' +
        formTicket.json()['datos']['ticket'],
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )

    logging.debug("Abrir pagina")
    return template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/cargarPagina.html",
        verb='POST',
        data='idPaso='+op+'&id='+op+'&pagina=1',
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )


def do_guardar(data):
    logging.debug("Guardar con datos %s", data)
    submit = template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/guardarPagina.html",
        verb='POST',
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        },
        data=data
    )

    dresp = submit.json()

    logging.debug("Guardar con datos, respuesta %s", dresp)
    template_request(
        dresp['datos']['url'],
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-Fetch-User": "?1",
        }
    )


def regenearte_captcha():
    logging.debug("Captcha: Regenerar")
    template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/regenerarCaptcha.html",
        verb='POST',
        validate_API=True,
        data='id=captcha',
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        }
    )

################################################################################################
# main
################################################################################################


pars = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

pars.add_argument('-v', '--verbose', action='count',
                  default=3, help="Incrementa la verbosidad")
argp_oblig = pars.add_argument_group('Obligatorios')
argp_opcionales = pars.add_argument_group('Opcionales')

argp_oblig.add_argument("-p", "--provincia",
                        help="Nombre de provincia. Vacío para consultar valores posibles", default=None, nargs='?')
argp_oblig.add_argument("-m", "--municipio",
                        help="Nombre de municipio. Vacío para consultar valores posibles", default=None, nargs='?')
argp_oblig.add_argument("-s", "--servicio",
                        help="Motivo de la cita. Vacío para consultar valores posibles", default=None, nargs='?')
argp_oblig.add_argument("-d", "--dni",
                        help="DNI/NIE", required=True)
argp_oblig.add_argument("-n", "--nombre",
                        help="Nombre", required=True)
argp_oblig.add_argument("-a1", "--apellido1",
                        help="Primer apellido", required=True)
argp_opcionales.add_argument("-a2", "--apellido2",
                             help="Segundo apellido")
argp_oblig.add_argument("-f", "--fecha",
                        help="Fecha de nacimiento (dd/mm/YYYY)", required=True,
                        type=lambda s: datetime.datetime.strptime(s, '%d/%m/%Y').strftime('%d/%m/%Y'))
argp_opcionales.add_argument("-x", "--citamin",
                             help="Fecha mínima de la cita (dd/mm/YYYY). Citas anteriores a dicha fecha serán ignoradas",
                             type=lambda s: datetime.datetime.strptime(
                                 s, '%d/%m/%Y'),
                             default=datetime.datetime.now(),
                             )
argp_opcionales.add_argument("-y", "--citamax",
                             help="Fecha máxima de la cita (dd/mm/YYYY). Citas posteriores a dicha fecha serán ignoradas",
                             type=lambda s: datetime.datetime.strptime(
                                 s, '%d/%m/%Y') + datetime.timedelta(hours=23, minutes=59, seconds=59),
                             )

argp_opcionales.add_argument("-z", "--horaobjetivo",
                             help="Hora cita (HH:MM). Se usará como preferencia para escoger en caso de haber más de una cita disponible",
                             type=lambda s: datetime.datetime.strptime(
                                 s, '%H:%M'),
                             default=None,
                             )


argp_oblig.add_argument("-o", "--output",
                             action='store',
                             required=True,
                             type=argparse.FileType('wb'), dest='output',
                             help="fichero PDF de la cita confirmada")


argp_opcionales.add_argument("-w", "--wait",
                             help="Tiempo de espera entre solicitudes",
                             type=int,
                             default=30,
                             )

# fcitamin
args_values = pars.parse_args()


log_levels = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}

logging.basicConfig(
    level=log_levels[min(args_values.verbose, max(log_levels.keys()))],
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

# logging.basicConfig(level=logging.INFO)


logging.debug("Funciones y variables inicializadas")

startweb = template_request(
    "https://www.tramita.gva.es/ctt-att-atr/asistente/iniciarTramite.html?tramite=CITA_PREVIA&version=2&idioma=es&idProcGuc=14104&idCatGuc=PR",
)


template_request(
    "https://www.tramita.gva.es/ctt-att-atr/j_spring_security_check",
    verb='POST',
    data='j_username=anonimo&j_password=' +
    html.fromstring(startweb.content).xpath(
        '//input[@id="j_password"]/@value')[0],
    extraHeaders={
        "Content-Type": "application/x-www-form-urlencoded",
    }
)
logging.debug("OK: Validar navegador")

getWebCSRF = template_request(
    "https://www.tramita.gva.es/ctt-att-atr/asistente/asistente.html",
)

tokenCSRF = re.search("tokenCSRF= ?\"([a-f0-9]+)\"", getWebCSRF.text).group(1)

if not tokenCSRF:
    raise RuntimeError("No token CSRF")

logging.debug("OK: Token CSRF")

################################################################################################
# Form ready to fill
################################################################################################


# El primer proces es identificarnos en la plataforma
logging.debug("Proceso Identificación: Start")
valores_identificacion = do_process('IDE')
logging.debug("Proceso Identificación: OK")

dataIDE = APIobject(valores_identificacion.json())

# Inicializar los 3
for e in ['provincia', 'municipio', 'servicio']:
    if not args_values.__dict__[e]:
        logging.critical(
            'Error de argumento "%s". Valores posibles:', e.upper())
        for v in dataIDE.getPossibleValue(APIconst[e.upper()]):
            logging.critical(v['descripcion'])
        sys.exit(1)

    dataIDE = dataIDE.fillValor(
        APIconst[e.upper()], args_values.__dict__[e]
    )

if not dataIDE.getDescripcion(APIconst.CENTRO):
    logging.fatal('No existe centro para el trámite "%s" en el municipio "%s" (%s)',
                  dataIDE.getDescripcion(APIconst.SERVICIO),
                  dataIDE.getDescripcion(APIconst.MUNICIPIO),
                  dataIDE.getDescripcion(APIconst.PROVINCIA))

dataIDE = dataIDE.addValor(
    APIconst.DNI, args_values.dni
).addValor(
    APIconst.NOMBRE, args_values.nombre
).addValor(
    APIconst.APELLIDO1, args_values.apellido1
).addValor(
    APIconst.FECHA, args_values.fecha
)
# .strftime('%d/%m/%Y')
logging.info("Datos personales listos.")
logging.info("Nombre   : %s", dataIDE._values[APIconst.NOMBRE]['valor'])
logging.info("Apell 1  : %s", dataIDE._values[APIconst.APELLIDO1]['valor'])
if dataIDE._values[APIconst.APELLIDO2]['valor']:
    logging.info("Nombre: %s", dataIDE._values[APIconst.APELLIDO2]['valor'])
logging.info("F. nacim.: %s", dataIDE._values[APIconst.FECHA]['valor'])
logging.info("Provincia: %s",
             dataIDE._values[APIconst.PROVINCIA]['valor']['descripcion'])
logging.info("Municipio: %s",
             dataIDE._values[APIconst.MUNICIPIO]['valor']['descripcion'])
logging.info("Servicio : %s",
             dataIDE._values[APIconst.SERVICIO]['valor']['descripcion'])
logging.info("F. min.  : %s", args_values.citamin.strftime('%d/%m/%Y'))
if args_values.citamax:
    logging.info("F. max.  : %s", args_values.citamax.strftime('%d/%m/%Y'))

if args_values.horaobjetivo:
    logging.info("Hora obj.: %s", args_values.horaobjetivo.strftime('%H:%M'))
if args_values.output:
    logging.info("Fichero  : %s", args_values.output.name)
logging.info("----------------------------------------")

# print("")

r = sr.Recognizer()

TOTAL_ATTEMPTS = 40
i = 0
while True:
    if i > TOTAL_ATTEMPTS:
        raise RuntimeError(
            "Excedido el máximo de intentos " + str(TOTAL_ATTEMPTS))

    sonidoCaptcha = template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/generarSonidoCaptcha.html?id=captcha&ts=" +
        str(round(time.time() * 1000)),
        extraHeaders={
            "Range": "bytes=0-",
        }
    )

    logging.info("Captcha: Intento " + str(i))

    # We slow down the audio in order to get better results
    rate = 16000*0.8
    final = io.BytesIO()

    with wave.open(io.BytesIO(sonidoCaptcha.content)) as w, wave.open(final, "wb") as ddd:
        # Get params
        params = w.getparams()
        # Change rate
        params = params._replace(framerate=rate)
        # Set new params
        ddd.setparams(params)
        # Get data
        audioFrames = w.readframes(w.getnframes())
        # Write new data
        ddd.writeframes(audioFrames)

    # final.seek(0)
    # with open("sonido_slow.wav", "wb") as f:
    #     f.write(final.read())

    final.seek(0)
    with sr.AudioFile(final) as source:
        audio = r.record(source)

        try:
            captcha = r.recognize_google(audio, language="es-ES")
            if not re.match('[0-9]{4}', captcha):
                logging.debug("Captcha: Formato incorrecto - " + captcha)
                regenearte_captcha()
                i += 1
                continue
            logging.info("Captcha: CANDIDATO " + captcha)
            dataIDE.setCaptcha(captcha)
        except:
            logging.debug("Captcha: No reconocido")
            regenearte_captcha()
            i += 1
            continue

    submitData = template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/guardarPagina.html",
        verb='POST',
        validate_API=True,
        extraHeaders={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-Token": tokenCSRF,
            "X-Requested-With": "XMLHttpRequest"
        },
        data=dataIDE.dumps(extra_att={'accion': 'VALIDAR'})
    )

    resp = submitData.json()

    logging.debug(resp)

    i += 1
    if 'finalizado' in resp['datos'] and resp['datos']['finalizado'] != 'n':
        break
    else:
        logging.info("Captcha: Captcha incorrecto")
        logging.debug(resp)
        logging.debug("Captcha: %s", resp)
        regenearte_captcha()
        continue


template_request(
    resp['datos']['url'],
    extraHeaders={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Sec-Fetch-User": "?1",
    }
)


################################################################################################
# Captcha passed
################################################################################################

logging.info("Captcha: OK")

while True:
    # Confirmamos criterios de búsqueda de cita

    logging.debug("Seleccionar criterios: Start")
    valores_criterios = do_process('CRITERIOS')
    logging.debug("Seleccionar criterios: OK")

    dataCRITERIOS = APIobject(valores_criterios.json()).addValor(
        APIconst.FECHA, args_values.citamin.strftime('%d/%m/%Y')
    )
    logging.debug("Seleccionar criterios: Objeto API ok")

    try:
        do_guardar(dataCRITERIOS.dumps(extra_att={'accion': 'SELECCION'}))
    except OldDateError as e:
        newdate = str(e)
        logging.warning("Fecha mínima (" + args_values.citamin.strftime('%d/%m/%Y') +
                        ") inferior al día actual. Nueva fecha mínima = " + newdate)
        args_values.citamin = datetime.datetime.strptime(newdate, '%d/%m/%Y')
        continue
    logging.debug("Seleccionar criterios: Finalizado")

    ################################################################################################
    # List books
    ################################################################################################

    # Seleccionamos la primera cita
    logging.debug("Seleccionar cita: Start")
    valores_seleccion = do_process('SELECCION')

    dataSELECCION = APIobject(valores_seleccion.json())
    logging.debug("Seleccionar cita: Objeto API ok")

    possibleValuesCitas = dataSELECCION.getPossibleValue('SEL_CITA')

    def wait_and_goback():
        logging.info(
            "Seleccionar cita: Sin citas disponibles. Reintentando en %s segundos", args_values.wait)

        # Wait and continue
        time.sleep(args_values.wait)

        # Step back
        logging.debug("Seleccionar cita: Regresando a criterios")
        do_guardar(dataSELECCION.dumps(extra_att={'accion': 'CRITERIOS'}))

    # If books are available, exit loop
    if possibleValuesCitas and (len(possibleValuesCitas) != 1 or possibleValuesCitas[0]['valor'] != 'SD'):

        possible_dates = [datetime.datetime.strptime(
            f['valor'], '%d/%m/%Y-%H:%M') for f in possibleValuesCitas]
        if args_values.citamax:
            possible_dates_filtered = list(
                filter(lambda f: (f <= args_values.citamax), possible_dates))
            if len(possible_dates_filtered) == 0:
                logging.warn("Hay citas disponibles (%s) después de su fecha máxima (%s). Considere cambiar/desactivar el parámetro -y/--citamax",
                             ' '.join([f.strftime('%d/%m/%Y-%H:%M') for f in possible_dates]), args_values.citamax.strftime('%d/%m/%Y'))
                wait_and_goback()
                continue

            possible_dates = possible_dates_filtered

        targetFechaCita = possibleValuesCitas[0]
        if args_values.horaobjetivo:
            logging.info("Seleccionando cita cercana a la hora " +
                         str(args_values.horaobjetivo.strftime('%H:%M')))

            selected = min(possible_dates, key=lambda t: abs(
                args_values.horaobjetivo.replace(year=t.year, month=t.month, day=t.day) - t))
            targetFechaCitaStr = selected.strftime('%d/%m/%Y-%H:%M')
            for f in possibleValuesCitas:
                if f['valor'] == targetFechaCitaStr:
                    targetFechaCita = f
                    break

        logging.info("Seleccionar cita: Cita para %s",
                     targetFechaCita['valor'])
        break

    wait_and_goback()


# First one is ok
dataSELECCION.addValor('SEL_CITA', targetFechaCita)

do_guardar(dataSELECCION.dumps(extra_att={'accion': 'CONFIRMAR'}))
logging.debug("Seleccionar cita: Finalizado")


################################################################################################
# Confirm book
################################################################################################

logging.debug("Confirmar cita: Start")
valores_confirmar = do_process('CONFIRMACION')

dataCONFIRMACION = APIobject(valores_confirmar.json())
logging.debug("Confirmar cita: Objeto API ok")

do_guardar(dataCONFIRMACION.dumps(extra_att={'accion': 'CONFIRMAR'}))
logging.debug("Confirmar cita: Finalizado")

logging.info("Cita confirmada")
# Cita confirmada

if args_values.output:
    do_process('IMPRIMIR')
    logging.info("Imprimir: Solicitar PDF")
    pdf = template_request(
        "https://www.tramita.gva.es/ctt-att-atr/asistente/fm/imprimir.html?accion=false",
    )

    logging.info("Imprimir: Guardar a %s", args_values.output.name)
    args_values.output.write(pdf.content)

logging.info("Finalizado :)")
