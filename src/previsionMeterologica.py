import requests, time
from datetime import datetime, date
from deep_translator import GoogleTranslator
import pandas as pd

# import matplotlib.pyplot as plt
from flask import request, Request
import random
import json
from os import remove
import folium
from folium.plugins import MiniMap
import os
import bcrypt
from geopy.geocoders import Nominatim
from functools import partial
from .db import con
from .utils import relative_to


def comprobar_usuario(email, pass_texto_plano):
    cur = con.cursor()
    cur.execute(
        "Select password FROM Usuarios WHERE email=?",
        (email,),
    )
    result = cur.fetchall()

    if len(result) == 0: return False

    pass_hasheada = result[0][0]
    pass_texto_plano = pass_texto_plano.encode()   
    if bcrypt.checkpw(pass_texto_plano, pass_hasheada):
        return True
    else:
        return False
    
    

def registro_usuarios(name, email, password):
    cur = con.cursor()
    cur.execute("SELECT count(email) FROM Usuarios WHERE email=?", (email,))
    resul = cur.fetchall()
    count = resul[0][0]
    
    if count == 0:
        password = password.encode()
        sal = bcrypt.gensalt()
        pass_hasheada = bcrypt.hashpw(password, sal)

        cur.execute(
            "INSERT INTO Usuarios(nombre,email,password,gustos,foto) values (?,?,?,?,?)",
            (name, email, pass_hasheada, None, None),
        )
        result = cur.fetchone()
        con.commit()
        return True
    
    con.commit()
    return False


def get_coordenadas(request: Request):
    coordenadas = request.cookies.get("ubicacion")
    if coordenadas == None:
        return
    coordenadas = json.loads(coordenadas)
    print(coordenadas)
    return coordenadas


def UbicacionTiempoReal():
    ubicacion_dict = get_coordenadas(request)
    coord = (
        str(ubicacion_dict.get("latitude")) + "," + str(ubicacion_dict.get("longitude"))
    )
    coord = coord.split(",", 1)
    latitud = float(coord[0])
    longitud = float(coord[1])

    mapa = folium.Map(
        location=[latitud, longitud], zoom_start=11.5, control_scale=True
    )  # Carga el mapa de Espana
    # #Ubicacion actual del usuario
    folium.Marker(
        location=[latitud, longitud], icon=folium.Icon(color="lightgreen")
    ).add_to(mapa)
    # #Colocamos el icono de ubicacion
    folium.Circle(
        location=[latitud, longitud],
        color="purple",
        fill_color="red",
        radius=50,
        weight=4,
        fill_opacity=0.5,
    ).add_to(mapa)
    mapa.save("templates/ubicacionReal.html")


# Funcion que devuelve el dia de la semana respecto a una fecha pasada como parametro
def Fecha_d(fecha):
    date_sr = str(pd.to_datetime(fecha))
    dt = datetime.fromisoformat(date_sr)
    dia_Semana = dt.strftime("%A")
    traductor = GoogleTranslator(source="en", target="es")
    resultado = traductor.translate(dia_Semana)
    return resultado


def Evento_Favorito(
    nombre,
    PrecioMin,
    PrecioMax,
    fecha,
    ciudad,
    direccion,
    venues,
    imagen,
    latitud,
    longitud,
    usuario,
):
    # Añadimos a la base de datos el evento elegido por el usuario como favorito
    cur = con.cursor()
    cur.execute(
        "SELECT count(Nombre) FROM EventosFavoritos WHERE Nombre=? AND Ciudad=? AND IdUsuario=?",
        (
            nombre,
            ciudad,
            usuario,
        ),
    )
    resul = cur.fetchall()
    count = resul[0][0]

    if count == 0:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO EventosFavoritos(Nombre,PrecioMax,PrecioMin,Fecha,Ciudad,Direccion,Imagen,Venues,Latitud,Longitud,IdUsuario,Usuario) values (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                nombre,
                PrecioMax,
                PrecioMin,
                fecha,
                ciudad,
                direccion,
                imagen,
                venues,
                latitud,
                longitud,
                usuario,
                usuario,
            ),
        )
        result = cur.fetchone()
        con.commit()
        TiempoParaEventos(latitud, longitud, ciudad)
        return True
    
    con.commit()
    return False


# Llamada de datos meterologicos para hacer un grafico por horas
def Prevision_Clima(city):
    datosObtenidos = requests.get(
        "http://api.openweathermap.org/data/2.5/forecast?q="
        + city
        + "&cnt=8&appid=8ca0c1c6f4748e36b8463b280a518364&units=Metric&lang=es"
    )
    datosFormatonJSON = datosObtenidos.json()

    lista = []
    info = {}
    temperatura = []
    por_horas = []

    lista_weather = datosFormatonJSON.get("list")
    # print(lista_weather)

    for weather in lista_weather:
        temp = weather.get("main").get("temp")
        temp = str(round(temp)) + "ºC"
        descr = weather.get("weather")[0].get("description")
        date = weather.get("dt_txt")
        valor = date.split(" ", 1)
        hora = valor[1][:5]

        info = {
            "temp": temp,
            "icono": weather.get("weather")[0].get("icon"),
            "lluvia": weather.get("pop"),
            "fecha": hora,
            "descripcion": descr,
        }
        temperatura.append(temp)
        por_horas.append(hora)
        lista.append(info)

    return (temperatura, por_horas, lista)


def climaDia(coordenadas):
    if coordenadas == "42.3443701,-3.6927629" or coordenadas == "42.34995,-3.69205":
        coordenadas = "41.6704100,-3.6892000"

    datosObtenidos = requests.get(
        "https://api.tutiempo.net/json/?lan=es&&units=Metric&apid=XwY44q4zaqXbxnV&ll="
        + coordenadas
    )
    datosFormatonJSON = datosObtenidos.json()

    dias = []
    dias.append(datosFormatonJSON.get("day2"))
    dias.append(datosFormatonJSON.get("day3"))
    dias.append(datosFormatonJSON.get("day4"))
    dias.append(datosFormatonJSON.get("day5"))
    dias.append(datosFormatonJSON.get("day6"))
    dias.append(datosFormatonJSON.get("day7"))

    if None in dias:
        return None

    lista = []
    url = "https://v5i.tutiempo.net"
    wd, wi = f"{url}/wd/big/black/", f"{url}/wi/"
    wi_icon = wi + "{style}/{size}/{icon}.png"
    wd_icon = wd + "{icon}.png"

    for d in dias:
        date = d.get("date")
        temp_min = d.get("temperature_min")
        temp_max = d.get("temperature_max")
        icono = d.get("icon")
        viento = d.get("wind")
        icono_viento = d.get("icon_wind")

        info = {
            "fecha": date,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "icono": icono,
            "viento": viento,
            "icono_viento": icono_viento,
            "wi_icon": wi_icon,
            "wd_icon": wd_icon,
        }

        lista.append(info)

    return lista


def ActualizarTiempoEventos(id):
    cur = con.cursor()
    cur.execute("SELECT DISTINCT Ciudad FROM EventosFavoritos WHERE IdUsuario=?", (id,))
    resul = cur.fetchall()

    for tupla in resul:
        for ciudad in tupla:
            cur.execute(
                "SELECT Latitud,Longitud FROM Ubicaciones WHERE Ciudad=?", (ciudad,)
            )
            infocity = cur.fetchall()

            if len(infocity) > 0:
                latitud = infocity[0][0]
                longitud = infocity[0][1]
                TiempoParaEventos(latitud, longitud, ciudad)
    con.commit()


def TiempoParaEventos(latitud, longitud, ciudad):
    cur = con.cursor()
    cur.execute("SELECT count(Ciudad) FROM Ubicaciones WHERE Ciudad=?", (ciudad,))
    resul = cur.fetchall()
    count = resul[0][0]

    if latitud != None and longitud != None:
        coordenadas = latitud + "," + longitud
        if coordenadas == "42.3443701,-3.6927629" or coordenadas == "42.34995,-3.69205":
            coordenadas = "41.6704100,-3.6892000"

        datosObtenidos = requests.get(
            "https://api.tutiempo.net/json/?lan=es&&units=Metric&apid=XwY44q4zaqXbxnV&ll="
            + coordenadas
        )
        datosFormatonJSON = datosObtenidos.json()
        dias = []
        dias.append(datosFormatonJSON.get("day1"))
        if None in dias:
            return None

        fecha = dias[0].get("date")
        TempMin = dias[0].get("temperature_min")
        TempMax = dias[0].get("temperature_max")
        icono = dias[0].get("icon")
        viento = dias[0].get("wind")
        iconoViento = dias[0].get("icon_wind")

        if count == 0:
            cur.execute(
                "INSERT INTO Ubicaciones(Ciudad,Fecha,TempMax,TempMin,Icono,Viento,IconoViento,Latitud,Longitud) values (?,?,?,?,?,?,?,?,?)",
                (
                    ciudad,
                    fecha,
                    TempMax,
                    TempMin,
                    icono,
                    viento,
                    iconoViento,
                    latitud,
                    longitud,
                ),
            )
            result = cur.fetchone()
            con.commit()
            return True

        else:
            cur.execute(
                "UPDATE Ubicaciones SET Fecha=?,TempMax=?,TempMin=?,Icono=?,Viento=?,IconoViento=? WHERE Ciudad=?",
                (fecha, TempMax, TempMin, icono, viento, iconoViento, ciudad),
            )
            result = cur.fetchone()
            con.commit()
            
            return True
        
    con.commit()
    return False


def Ubicaciones(id):
    # Extraemos de la base de datos los eventos elegidos por el usuario como favoritos

    cur = con.cursor()
    cur.execute("SELECT DISTINCT Ciudad FROM EventosFavoritos WHERE IdUsuario=?", (id,))
    resul = cur.fetchall()

    lista = []
    url = "https://v5i.tutiempo.net"
    wd, wi = f"{url}/wd/big/black/", f"{url}/wi/"
    wi_icon = wi + "{style}/{size}/{icon}.png"
    wd_icon = wd + "{icon}.png"

    for tupla in resul:
        for ciudad in tupla:
            if ciudad == "Vitoria-Gasteiz":
                ciudad = "Vitoria"

            cur.execute("SELECT * FROM Ubicaciones WHERE Ciudad=?", (ciudad,))
            infocity = cur.fetchall()

            if len(infocity) > 0:
                info = {
                    "ciudad": infocity[0][0],
                    "fecha": infocity[0][1],
                    "temp_min": infocity[0][3],
                    "temp_max": infocity[0][2],
                    "icono": infocity[0][4],
                    "viento": infocity[0][5],
                    "icono_viento": infocity[0][6],
                    "wi_icon": wi_icon,
                    "wd_icon": wd_icon,
                }
                lista.append(info)

    con.commit()
    return lista


def Preparese_Para_Su_Dia(city):
    lista = Prevision_Clima("Burgos")
    datos = lista[2][0]
    info = {}

    today = date.today()
    fecha = today.strftime("%a, %d %b %Y")
    paraguas = "No es necesario"
    abrigo = "Ropa fina"
    sensacion_termica = datos.get("temp")
    al_aire_libre = datos.get("descripcion")
    temp = datos.get("temp")
    temp = temp.split("º", 1)

    if datos.get("lluvia") > 30:
        paraguas = "Es necesario"
    if int(temp[0]) < 14:
        abrigo = "Ropa gruesa"
    if int(temp[0]) > 23:
        abrigo = "Ropa de verano"

    info = {
        "paraguas": paraguas,
        "abrigo": abrigo,
        "sensTermica": sensacion_termica,
        "aireLibre": al_aire_libre,
        "fecha": fecha,
    }

    return info


def load_file_json_events():
    eventos_path = relative_to(__file__,"eventos.json")
    with open(eventos_path, "r") as fp:
        data = json.load(fp)
        return data

def save_file_json_events(my_dict):
    eventos_path = relative_to(__file__,"eventos.json")
    with open(eventos_path, "w") as fp:
        json.dump(my_dict, fp)


def load_file_json_news():
    noticias_path = relative_to(__file__,"noticias.json")
    with open(noticias_path, "r") as fp:
        data = json.load(fp)
        return data


def save_file_json_news(my_dict):
    noticias_path = relative_to(__file__,"noticias.json")
    with open(noticias_path, "w") as fp:
        json.dump(my_dict, fp)


def Eventos(id):
    # Extraemos de la base de datos los eventos elegidos por el usuario como favoritos
    cur = con.cursor()
    cur.execute("SELECT * FROM EventosFavoritos WHERE IdUsuario=?", (id,))
    resul = cur.fetchall()
    con.commit()

    mapa = folium.Map(
        location=[40.463667, -3.74922], zoom_start=6.45, control_scale=True
    )  # Carga el mapa de Espana

    for tupla in resul:
        latitud = tupla[8]
        longitud = tupla[9]
        ubicacion = tupla[7]
        evento = "<b>Evento: "
        evento += tupla[0]
        evento += "</b>"

        # Ubicaciones de las cuales se muestran los eventos y noticias en el mapa
        folium.Marker(
            location=[latitud, longitud],
            popup=evento,
            icon=folium.Icon(color="lightgreen"),
        ).add_to(mapa)
        # Colocamos el icono de ubicacion
        folium.Circle(
            location=[latitud, longitud],
            color="purple",
            fill_color="red",
            radius=50,
            weight=4,
            fill_opacity=0.5,
            tooltip=ubicacion,
        ).add_to(mapa)

    minimapa = MiniMap()
    mapa.add_child(minimapa)

    mapa_path = relative_to(__file__,"templates/mapa.html")

    mapa.save(mapa_path)


def Eventos_DB_Mapa(id):
    # Extraemos de la base de datos los eventos elegidos por el usuario como favoritos
    cur = con.cursor()
    cur.execute("SELECT * FROM EventosFavoritos WHERE IdUsuario=?", (id,))
    resul = cur.fetchall()
    con.commit()
    return resul


def BorrarEventoFav(nombre, ciudad):
    cur = con.cursor()
    cur.execute(
        "DELETE FROM EventosFavoritos WHERE Nombre=? AND Ciudad=?",
        (
            nombre,
            ciudad,
        ),
    )
    con.commit()


def get_imagen(city):
    url = "https://bing-image-search1.p.rapidapi.com/images/search"
    count = 4
    params = {"q": city, "count": count, "mkt": "es-ES"}

    headers = {
        "X-RapidAPI-Key": "275bb62fcfmshe06f494e237a78cp174832jsn0dbb9c290237",
        "X-RapidAPI-Host": "bing-image-search1.p.rapidapi.com",
    }

    response = requests.request("GET", url, headers=headers, params=params)

    data = response.json()

    results = data["value"]

    index = random.randint(0, count - 1)
    img = results[index]

    return img["contentUrl"], img["thumbnailUrl"]


def NoticiasApi():
    API_KEY = "pub_7421c00b07c3b0a1ab68df5be83ae037be9f"
    datosObtenidos = requests.get(
        "https://newsdata.io/api/1/news?apikey=pub_7421c00b07c3b0a1ab68df5be83ae037be9f&q=news&language=es&country=es"
    )
    datosFormatonJSON = datosObtenidos.json()

    if (not "totalResults" in datosFormatonJSON) or int(
        datosFormatonJSON.get("totalResults")
    ) <= 5:
        datosFormatonJSON = load_file_json_news()
    else:
        save_file_json_news(datosFormatonJSON)

    return datosFormatonJSON.get("results")


def infoEventosApi(idEvento):
    datosObtenidos = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json?apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&id="
        + idEvento
    )
    datosFormatonJSON = datosObtenidos.json()
    info = datosFormatonJSON.get("_embedded")
    evento = info.get("events")[0]

    nombre = evento.get("name")
    imagen = evento.get("images")[0].get("url")
    precioMin = 0
    precioMax = 0
    if "priceRanges" in evento:
        precioMin = evento.get("priceRanges")[0].get("min")
        precioMax = evento.get("priceRanges")[0].get("max")

    fecha = evento.get("dates").get("start").get("localDate")
    masInfo = evento.get("_embedded")
    ciudad = masInfo.get("venues")[0].get("city").get("name")
    direccion = masInfo.get("venues")[0].get("address").get("line1")
    venues = masInfo.get("venues")[0].get("name")
    latitud = masInfo.get("venues")[0].get("location").get("latitude")
    longitud = masInfo.get("venues")[0].get("location").get("longitude")

    infoEvento = {
        "nombre": nombre,
        "PrecioMin": precioMin,
        "PrecioMax": precioMax,
        "Fecha": fecha,
        "Ciudad": ciudad,
        "Direccion": direccion,
        "Venues": venues,
        "Imagen": imagen,
        "Latitud": latitud,
        "Longitud": longitud,
    }

    return infoEvento


def eventosApi():
    datosObtenidos = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json?apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&language=es&countryCode=ES"
    )
    datosFormatonJSON = datosObtenidos.json()

    if (datosFormatonJSON.get("page").get("totalElements") == 0) or (
        int(datosFormatonJSON.get("page").get("totalElements")) < 5
    ):
        datosFormatonJSON = load_file_json_events()
    else:
        save_file_json_events(datosFormatonJSON)

    info = datosFormatonJSON.get("_embedded")

    eventos = info.get("events")
    get_image = lambda event: event["images"][-1]
    get_categoria = lambda categ: categ["classifications"][0]["segment"]
    ubicacion = "España"
    categoria = "Todas"

    return (eventos, get_image, get_categoria, ubicacion, categoria)


def PeticionCoordenadas(coordenadas):
    geolocator = Nominatim(user_agent="joselii6ito@gmail.com")
    geocode = partial(geolocator.reverse, language="es")
    info = geocode(coordenadas)
    if info != None:
        address = info.raw["address"]
        city: str = address.get("city") or address.get("village")
        print(f"Info de {city}: ")
        return city
    else:
        return None


def PeticionToponimo(city):
    geolocator = Nominatim(user_agent="joselii6ito@gmail.com")
    location = geolocator.geocode(city, language="es", country_codes="ES")
    if location != None:
        latitud = str(location.latitude)
        longitud = str(location.longitude)
        latitud += "," + longitud
        return latitud
    else:
        return None
