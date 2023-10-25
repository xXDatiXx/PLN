# Codificación en formato UTF-8

# Importar las librerías necesarias de trabajo en el Skill (No modificar las presente)
import logging
import ask_sdk_core.utils as ask_utils
import os
import json
import locale
import requests
import calendar
import gettext
from datetime import datetime
from pytz import timezone
from ask_sdk_s3.adapter import S3Adapter

# El adaptador S3 permite una conexión virtual con un Bucket de información (S3)
# de AWS para almacenar datos, en este caso la fecha de cumpleaños del usuario
s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])


from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractRequestInterceptor, AbstractExceptionHandler)
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

from ask_sdk_core.utils import is_request_type, is_intent_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


#---------------------------------------------- Definición de las clases comunes-----------------------------------------------------------------------------

# Se activa al inicio de la conversación (En cuanto se abre la Skill)
class LaunchRequestHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech = "Hola! Bienvenido a Feliz Cumpleaños de ACTUMLOGOS. ¿Cuál es tu fecha de nacimiento?"
        reprompt = "Yo nací el 6 de noviembre del año 2014. ¿Y tú?"

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


# Se activa para cuando se solicita ayuda (Para saber qué puede hacer esta Skill)
class HelpIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Como soy muy lista, puedo acordarme de la fecha de tu cumpleaños. Puedes decirme, 'recuerda mi cumpleaños', o simplemente decirme la fecha. Vamos, puébalo ahora!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# Se activa cuando se cancela el intent (Se pude salir del flujo)
class CancelOrStopIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        speak_output = "Hasta luego, fue un gusto hablar contigo, espero que regreses pronto"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


# Para el cierre de sesión (Salida por completo de la Skill)
class SessionEndedRequestHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = "Nos escuchamos luego"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )



# Se activa de manera automática cuando Alexa no logra entender (Encontrar un Intent) para la petición que realizaste 
class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):

        logger.error(exception, exc_info=True)
        speak_output = "Una disculpa pero no te entendí, ¿Podrías repetirlo con otras palabras por favor?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# -------------------------------------------Definición de clase para recordar cumpleaños-------------------------------------------------------------

# Para capturar en el sistema tu cumpleaños (Por primera vez)
# Para cuando Alexa aún no sabe tu fecha de cumpleaños porque no se la has indicado
class BirthdayIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return is_intent_name("CapturarFechaIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        skill_locale = handler_input.request_envelope.request.locale

        # Extraer el valor del año con la entidad anio
        year = slots["anio"].value
        # Extraer el valor del mes con la entidad mes
        month = slots["mes"].value
        # Extraer el valor del día con la entidad día
        day = slots["dia"].value

        # Convertimos el mes en un número en lugar de un String (del diccionario personalizado)
        # Llamamos a un método en la parte de abajo
        month_as_index = self.monthIndex(month[:3])
        
        # Guardamos los valores de Slots dentro de atributos de sesión
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['anio'] = year
        session_attr['mes'] = month_as_index
        session_attr['dia'] = day

        # Guardamos los atributos de sesión como atributos persistentes (Para quedar dentro de S3)
        handler_input.attributes_manager.persistent_attributes = session_attr
        handler_input.attributes_manager.save_persistent_attributes()

        # Nos aseguramos que los atributos estén en el orden correcto (día / mes / año) para México
        # Llamamos a un método en la parte de abajo
        date = self.formatDate(year, month, day, skill_locale)

        # Decimos un mensaje para informar al usuario cuál fecha estamos registrando
        #Validamos que elementos tenemos y cuales no
        if date[0] != None and date[1] != None and date [2] != None:
            texto = "Genial!, me acordaré de tu fecha de nacimiento: {} {} {}."
            speech = texto.format(date[0], date[1], date[2])
        if date[0] == None and date[1] != None and date [2] != None:
            texto = "Genial!, me acordaré de tu fecha de nacimiento: {} {}."
            speech = texto.format(date[1], date[2]) 
        
        handler_input.response_builder.speak(speech)
        handler_input.response_builder.set_should_end_session(True)
        return handler_input.response_builder.response

    # Método para ordenar la fecha (día / mes / año) para México
    def formatDate(self, year, month, day, skill_locale):
        if skill_locale == 'en-US':
            # MM/DD/YYYY para Estados Unidos
            date = [month, day, year]
        elif skill_locale == 'ja-JP':
            # YYYY/MM/DD para Japón
            date = [year, month, day]
        else:
            # DD/MM/YYY otors como México
            date = [day, month, year]
        return date

    # Método para convertir los meses en número, Ejemplo Julio -> 7  /  Octubre -> 10
    def monthIndex(self, month):
        month_list = list(calendar.month_name)
        i = 0
        while i < len(month_list):
            if (month.lower() in month_list[i].lower()):
                return i
            i += 1
            

        
# -------------------------------------------Definición de clase cuando ya se dio el cumpleaños-------------------------------------------------------------

# Para recordar algún dato que se le haya dado a Alexa en alguna ejecución anterior de la Skill
# Esta clase se debe activar si ya se le ha dado a Alexa la fecha de cumpleaños
class HasBirthdayLaunchRequestHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        # Se extraen los atributos persistentes (Y se revisa si están presentes)
        attr = handler_input.attributes_manager.persistent_attributes
        attributes_are_present = ("anio" in attr and "mes" in attr and "dia" in attr)

        return attributes_are_present and ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        attr = handler_input.attributes_manager.persistent_attributes
        
        year = int(attr['anio'])
        month = attr['mes']
        day = int(attr['dia'])
        
        error_timezone_speech = "No he potido determinar tu zona horaria. Verifica la configuración de tu dispositivo, y intenta otra vez."
        
        # Obtener el ID del dispositivo
        sys_object = handler_input.request_envelope.context.system
        device_id = sys_object.device.device_id

        # Obtener la información de seteo del API de Alexa para comunicación con el EndPoint
        api_endpoint = sys_object.api_endpoint
        api_access_token = sys_object.api_access_token

        # Construir una URL API Timezone de sistema
        url = '{api_endpoint}/v2/devices/{device_id}/settings/System.timeZone'.format(api_endpoint=api_endpoint, device_id=device_id)
        headers = {'Authorization': 'Bearer ' + api_access_token}

        userTimeZone = ""
        
        # Tratar de obtener los datos almacenados en S3
        try:
	        r = requests.get(url, headers=headers)
	        res = r.json()
	        logger.info("Device API result: {}".format(str(res)))
	        userTimeZone = res
        except Exception:  
	        handler_input.response_builder.speak(error_timezone_speech)
	        return handler_input.response_builder.response
	        
        # Obtener la fecha actual
        now_time = datetime.now(timezone(userTimeZone))

        # Remover la hora actual para que no afecte el cálculo
        now_date = datetime(now_time.year, now_time.month, now_time.day)
        current_year = now_time.year

        # Obtener la fecha del siguiente cumpleaños
        next_birthday = datetime(current_year, month, day)

        # Verificar si se necesita ajustar el cumpleaños por un año
        if now_date > next_birthday:
            next_birthday = datetime(
                current_year + 1,
                month,
                day
            )
            current_year += 1
            
        # Calcular días que quedan hasta el siguiente cumpleaños
        diff_days = abs((now_date - next_birthday).days)

        # Si es el cumpleaños del usuario
        if now_date == next_birthday:
            speak_output = "Muy Feliz Cumpleaños! Hoy cumples {} año!".format(current_year - year)
        # Si no es el cumpleaños del usuario
        else:
            if diff_days > 1:
                speak_output = "Hola otra vez! Faltan {} días para que cumplas {} años.".format(diff_days, current_year-year)
            elif diff_days < 2:
                speak_output = "Hola otra vez! Falta {} día para que cumplas {} año.".format(diff_days, current_year - year)

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )
	        

    
#---------------------------------------------- Llamadas a sistema -----------------------------------------------------------------------------------

# Aquí se deben de incluir todas las clases nativas (Intents) definidos por Amazon
# y los nuevos que el usuario haya decidido incluir

# El adaptador de persistencia permite continuar con la información almacenada en S3 ficticia
sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

# Clase que se activa cuando ya se tiene el cumpleaños. Es importante que esté declarada antes 
# que LaunchRequestHandler para que se intente activar antes, en caso de que ya se tenga la 
# fecha de cumpleaños
sb.add_request_handler(HasBirthdayLaunchRequestHandler())

# Clase de lanzamiento o inicial (Si no tiene el cumpleaños)
sb.add_request_handler(LaunchRequestHandler())

# Clases para registrar el cumpleaños
sb.add_request_handler(BirthdayIntentHandler())

# Clases definidas (Obligatorias) por Amazon
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Clases para administración de errores en la conversación
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()