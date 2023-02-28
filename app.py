from flask import Flask, render_template, request, redirect, url_for, Request, session, flash
import requests
import json
from GestorGeocoding import *
import folium
from folium.plugins import MiniMap
from bing_image_downloader import downloader
import pandas as pd
from typing import Literal
import random
import sqlite3
from previsionMeterologica import *
from urllib.parse import parse_qsl


app = Flask(__name__)

app.secret_key = b'\xe1\xeb\xed3\x1ew\x155\xeb*&c\\\x8f\xeb8'

@app.before_request
def antes_de_cada_peticion():
    ruta = request.path
    # Si no ha iniciado sesión y no quiere ir a algo relacionado al login, lo redireccionamos al login
    if not 'usuario' in session and ruta != "/login" and ruta != "/registro" and not ruta.startswith("/static"):
        flash("Inicia sesión para continuar")
        return render_template("/login.html")

# Cerrar sesión
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect("/login")


@app.route("/", methods=["POST", "GET"])
def index():
    return render_template("login.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if comprobar_usuario(email, password):
            
            session["usuario"] = email 
            url = ""
            return render_template("principal.html", url=url)

        elif email != "" or password != "":
            mensaje = "Username or Password incorrect"
            return render_template("login.html", mensaje=mensaje)
        else:
            return render_template("login.html")

    else:
        ubicacion_dict = get_coordenadas(request)
        return render_template("login.html")


@app.route("/registro", methods=["POST", "GET"])
def registro():
    if request.method == "POST":
        nombre = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if nombre == "" or email == "" or password == "":
            return render_template("registro.html")

        if registro_usuarios(nombre, email, password):
            mensaje = "Registered User"
            return render_template("registro.html", mensaje=mensaje)
        else:
            mensaje = "User already exists"
            return render_template("registro.html", mensaje=mensaje)
    else:
        return render_template("registro.html")


@app.route("/principal", methods=["POST", "GET"])
def principal():
    return render_template("principal.html")

@app.route("/eventos")
def eventos():
    info = eventosApi()
    eventos = info[0] 
    get_image = info[1]
    get_categoria = info[2]
    return render_template("eventos.html", eventos=eventos, get_img=get_image, get_categ=get_categoria)  


@app.route("/favoritos")
def favoritos():
    nombre = request.args.get("name") #Obtenemos la info del evento
    precioMin = request.args.get("min") #Obtenemos la info del evento
    precioMax = request.args.get("max") #Obtenemos la info del evento
    fecha = request.args.get("date") #Obtenemos la info del evento
    ciudad = request.args.get("city") #Obtenemos la info del evento
    direccion = request.args.get("dir") #Obtenemos la info del evento
    venues = request.args.get("venues") #Obtenemos la info del evento
    imagen = request.args.get("image") #Obtenemos la info del evento
    latitud = request.args.get("lat")
    longitud = request.args.get("lon")
    usuario = session["usuario"] 

    infoEvento = {"nombre":nombre,
                  "PrecioMin":precioMin,
                  "PrecioMax":precioMax,
                  "Fecha":fecha,
                  "Ciudad":ciudad,
                  "Direccion":direccion,
                  "Venues":venues,
                  "Imagen":imagen}
    
    valor = False

    if nombre !=None and precioMax !=None and precioMin !=None and fecha !=None and ciudad !=None and direccion !=None and venues !=None and imagen !=None:
        valor = Evento_Favorito(nombre,precioMin,precioMax,fecha,ciudad,direccion,venues,imagen,latitud,longitud,usuario)
    
    if valor:
        mensaje = "Evento añadido a favoritos"
        return render_template("infoEvento.html",info=infoEvento,mensaje=mensaje)

    mensaje = "Este evento ya existe en favoritos"
    return render_template("infoEvento.html",info=infoEvento,mensaje=mensaje)
    

@app.route("/infoEvento")
def infoEventos():
    id_evento = request.args.get("id") #Obtenemos el id del evento
    infoEvento = infoEventosApi(id_evento)
    return render_template("infoEvento.html",info=infoEvento)


@app.route("/eventosUbic", methods=["POST"])
def eventosPorUbicacion():
    city = request.form["search"]
    categoria = request.form["categorias"]
    datosObtenidos = ""

    if city != " " and categoria != "disabled selected":
        datosObtenidos = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json?classificationName="
            + categoria
            + "&city="
            + city
            + "&apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&language=es&countryCode=ES"
        )

    elif city != " " and categoria == "disabled selected":
        datosObtenidos = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json?&city="
            + city
            + "&apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&language=es&countryCode=ES"
        )

    elif city == " " and categoria != "disabled selected":
        datosObtenidos = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json?classificationName="
            + categoria
            + "&apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&language=es&countryCode=ES"
        )
    else:
        datosObtenidos = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json?apikey=FKM66NQuNZ4k6GAAEJWl57l2tYDQ7VTA&language=es&countryCode=ES"
        )
        datosFormatonJSON = datosObtenidos.json()
        if int(datosFormatonJSON.get("page").get("totalElements")) > 4:
            save_file_json_events(datosFormatonJSON)

    datosFormatonJSON = datosObtenidos.json()

    if (datosFormatonJSON.get("page").get("totalElements") == 0) or (
        int(datosFormatonJSON.get("page").get("totalElements")) <= 5
    ):
        datosFormatonJSON = load_file_json_events()

    info = datosFormatonJSON.get("_embedded")
    eventos = info.get("events")

    if len(eventos) == 0:
        return render_template("eventos.html")

    get_image = lambda event: event["images"][-1]
    get_categoria = lambda categ: categ["classifications"][0]["segment"]

    return render_template(
        "eventosUbic.html", eventos=eventos, get_img=get_image, get_categ=get_categoria
    )


@app.route("/noticias")
def Noticias():
    info = NoticiasApi()
    return render_template("noticias.html", noticias=info)


@app.route("/noticiasUbic", methods=["POST", "GET"])
def NoticiasPorUbic():
    city = request.form["search"]
    categoria = request.form["categorias"]

    if city != "" and categoria != "disabled selected":
        datosObtenidos = requests.get(
            "https://newsdata.io/api/1/news?apikey=pub_7421c00b07c3b0a1ab68df5be83ae037be9f&q=news%20AND%20&country=es"
            + city
            + "&language=es&category="
            + categoria
        )

    elif city != "" and categoria == "disabled selected":
        datosObtenidos = requests.get(
            "https://newsdata.io/api/1/news?apikey=pub_7421c00b07c3b0a1ab68df5be83ae037be9f&q=news%20AND%20&country=es"
            + city
            + "&language=es"
        )

    elif city == "" and categoria != "disabled selected":
        datosObtenidos = requests.get(
            "https://newsdata.io/api/1/news?apikey=pub_7421c00b07c3b0a1ab68df5be83ae037be9f&q=news&language=es&country=es&category="
            + categoria
        )

    else:
        datosObtenidos = requests.get(
            "https://newsdata.io/api/1/news?apikey=pub_7421c00b07c3b0a1ab68df5be83ae037be9f&q=news&language=es&country=es"
        )
        datosFormatonJSON = datosObtenidos.json()
        if ("totalResults" in datosFormatonJSON) and int(
            datosFormatonJSON.get("totalResults")
        ) > 5:
            save_file_json_news(datosFormatonJSON)

    datosFormatonJSON = datosObtenidos.json()

    if (not "totalResults" in datosFormatonJSON) or int(
        datosFormatonJSON.get("totalResults")
    ) < 1:
        datosFormatonJSON = load_file_json_news()

    info = datosFormatonJSON.get("results")

    if len(info) == 0:
        return render_template("noticias.html")

    return render_template("noticiasUbic.html", noticias=info)

@app.route("/searchMeterologiaUbic", methods=["POST"])
def SearchMeterologiaUbic():
    city = request.form["search"]

    if (city =="") or (city == " ") or (city == "   "):
        mensaje = "Para esta ubicación no está disponible el servicio."
        return render_template("meterologiaUbicError.html",mensaje=mensaje)


    datosObtenidos = requests.get(
        "http://api.openweathermap.org/data/2.5/weather?q="
        + city
        + "&appid=8ca0c1c6f4748e36b8463b280a518364&units=Metric&lang=es"
    )

    datosFormatonJSON = datosObtenidos.json()
    if datosFormatonJSON.get("cod") == "404":
        mensaje = "Este Servicio no se encuentra disponible en este momento."
        return render_template("meterologiaUbicError.html",mensaje=mensaje)

    info = datosFormatonJSON.get("main")
    weather = datosFormatonJSON.get("weather")[0]
    today = date.today()
    fecha = today.strftime("%m-%d-%Y")

    meterologia = {
        "fecha": fecha,
        "city": city,
        "description": weather["description"],
        "clim": weather["main"],
        "icon": weather["icon"],
        "temp": round(info["temp"]),
        "temp_min": round(info["temp_min"]),
        "temp_max": round(info["temp_max"]),
        "pressure": info["pressure"],
        "humidity": info["pressure"],
        "windspeed": datosFormatonJSON["wind"]["speed"],
    }

    coord = PeticionToponimo(city)
    clima7d = climaDia(coord)

    if clima7d == None :
        mensaje = "La Previsión del Tiempo no está disponible en este momento."
        return render_template("meterologiaUbic.html",weather=meterologia,clima7d=[],preparase={},mensaje=mensaje)
    
    
    preparase = Preparese_Para_Su_Dia(city)

    return render_template(
        "meterologiaUbic.html",
        weather=meterologia,
        clima7d=clima7d,
        preparase=preparase,
    )


@app.route("/meterologiaUbic")
def meterologiaUbic():
    ubicacion_dict = get_coordenadas(request)
    coord = (
        str(ubicacion_dict.get("latitude")) + "," + str(ubicacion_dict.get("longitude"))
    )
    print("Coordenadas Actuales: ",coord)
    city = PeticionCoordenadas(coord)
    cont = 1
    print("Valor de City: ",city)

    while city == None and cont < 6:
        city = PeticionCoordenadas(coord)
        cont = cont + 1

    if city == None:
        mensaje = "Este Servicio no se encuentra disponible en este momento."
        return render_template("meterologiaUbicError.html",mensaje=mensaje)

    datosObtenidos = requests.get(
        "http://api.openweathermap.org/data/2.5/weather?q="
        + city
        + "&appid=8ca0c1c6f4748e36b8463b280a518364&units=Metric&lang=es"
    )

    datosFormatonJSON = datosObtenidos.json()
    if datosFormatonJSON.get("cod") == "404":
        mensaje = "Este Servicio no se encuentra disponible en este momento."
        return render_template("meterologiaUbicError.html",mensaje=mensaje)

    info = datosFormatonJSON.get("main")
    weather = datosFormatonJSON.get("weather")[0]
    today = date.today()
    fecha = today.strftime("%m-%d-%Y")

    meterologia = {
        "fecha": fecha,
        "city": city,
        "description": weather["description"],
        "clim": weather["main"],
        "icon": weather["icon"],
        "temp": round(info["temp"]),
        "temp_min": round(info["temp_min"]),
        "temp_max": round(info["temp_max"]),
        "pressure": info["pressure"],
        "humidity": info["pressure"],
        "windspeed": datosFormatonJSON["wind"]["speed"],
    }

    clima7d = climaDia(coord)

    if clima7d == None :
        mensaje = "La Previsión del Tiempo no está disponible en este momento."
        return render_template("meterologiaUbic.html",weather=meterologia,clima7d=[],preparase={},mensaje=mensaje)
    
    
    preparase = Preparese_Para_Su_Dia(city)

    return render_template(
        "meterologiaUbic.html",
        weather=meterologia,
        clima7d=clima7d,
        preparase=preparase,
    )
      
@app.route("/mapa")
def mapa():
    usuario = session["usuario"]
    Eventos(usuario)
    return render_template("mapa.html")

@app.route("/ubicacionReal")
def UbicacionReal():
    UbicacionTiempoReal()
    return render_template("ubicacionReal.html")


@app.route("/EventosFavoritos")
def EventosFavoritos():
    usuario = session["usuario"]
    eventos = Eventos_DB_Mapa(usuario)
    return render_template("EventosFavoritos.html",eventos=eventos)

@app.route("/BorrarEventoFavorito")
def BorrarEventoFavorito():
    usuario = session["usuario"]
    nombre = request.args.get("name")
    ciudad = request.args.get("city")

    BorrarEventoFav(nombre,ciudad)
    eventos = Eventos_DB_Mapa(usuario)
    return render_template("EventosFavoritos.html",eventos=eventos)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
