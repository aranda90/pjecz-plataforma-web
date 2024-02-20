@edictos.route("/edictos/nuevo/notaria", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_notaria():
    """Subir Edicto como notaria"""
    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()

    if ROL_NOTARIA in current_user_roles:
        hoy = datetime.date.today()
        hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
        limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_DIAS)

        # Validar autoridad
        autoridad = current_user.autoridad
        if autoridad is None or autoridad.estatus != "A":
            flash("El juzgado/autoridad no existe o no es activa.", "warning")
            return redirect(url_for("edictos.list_active"))
        if not autoridad.distrito.es_distrito_judicial:
            flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
            return redirect(url_for("edictos.list_active"))
        if not autoridad.es_jurisdiccional:
            flash("El juzgado/autoridad no es jurisdiccional.", "warning")
            return redirect(url_for("edictos.list_active"))
        if autoridad.directorio_edictos is None or autoridad.directorio_edictos == "":
            flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
            return redirect(url_for("edictos.list_active"))

        form = EdictoNewNotariaForm(CombinedMultiDict((request.files, request.form)))
        print("Solo me quede hasta aqui")
        if form.validate_on_submit():
            es_valido = True
            print("Entre a la validacion")

            fecha = form.fecha.data
            if not limite_dt <= datetime.datetime(year=fecha.year, month=fecha.month, day=fecha.day):
                flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
                form.fecha.data = hoy
                es_valido = False

            try:
                acuses_num = form.acuses_num.data
            except (ValueError, TypeError):
                flash("Especificar una cantidad publicaciones válida.", "warning")
                es_valido = False

            descripcion = safe_string(form.descripcion.data)
            if not descripcion:
                flash("La descripción es incorrecta.", "warning")
                es_valido = False

            if not es_valido:
                return render_template("edictos/new_for_notarias.jinja2", form=form)

            archivo = request.files.get("archivo")
            if not archivo or archivo.filename == "":
                flash("Archivo requerido.", "warning")
                es_valido = False
            elif "." not in archivo.filename or archivo.filename.rsplit(".", 1)[1] != "pdf":
                flash("No es un archivo PDF.", "warning")
                es_valido = False

            if not es_valido:
                return render_template("edictos/new_for_notarias.jinja2", form=form)

            # Si la fecha del edicto es igual a la fecha actual, insertar el registro
            if es_valido:
                edicto = Edicto(
                    autoridad=autoridad,
                    fecha=fecha,
                    acuses_num=int(acuses_num),
                    descripcion=descripcion,
                )
                edicto.save()
                print("Hice el insert")

                # Insertar las fechas de acuses ingresadas manualmente por el usuario
                nuevas_fechas_acuses = [getattr(form, f"fecha_acuse_{i}").data for i in range(1, acuses_num + 1)]
                for fecha_acuse in nuevas_fechas_acuses:
                    acuse = EdictoAcuse(
                        edicto_id=edicto.id,
                        fecha=fecha_acuse,
                    )
                    acuse.save()

                # Elaborar nombre del archivo
                fecha_str = fecha.strftime("%Y-%m-%d")
                elementos = [fecha_str]
                elementos.append(safe_string(descripcion, max_len=64).replace(" ", "-"))
                elementos.append(edicto.encode_id())
                archivo_str = "-".join(elementos) + ".pdf"

                # Elaborar ruta Autoridad/YYYY/MES/archivo.pdf
                ano_str = fecha.strftime("%Y")
                mes_str = mes_en_palabra(fecha.month)
                ruta_str = str(Path(autoridad.directorio_edictos, ano_str, mes_str, archivo_str))

                # Crear o recuperar la instancia de blob
                deposito = current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"]
                storage_client = storage.Client()
                bucket = storage_client.bucket(deposito)
                blob = bucket.blob(ruta_str)

                # Subir el archivo
                blob.upload_from_string(archivo.stream.read(), content_type="application/pdf")
                url = blob.public_url

                # Actualizar el nombre del archivo y el url
                edicto.archivo = archivo_str
                edicto.url = url
                edicto.save()

                # Mostrar mensaje de éxito e ir al detalle
                bitacora = new_notaria_success(edicto)
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)

        # Asignar los valores de distrito, autoridad y fecha dentro del bloque if ROL_notaria
        form.distrito.data = autoridad.distrito.nombre
        form.autoridad.data = autoridad.descripcion
        form.fecha.data = hoy
        print("No hace nada y me retorna acá")
        return render_template("edictos/new_for_notarias.jinja2", form=form)