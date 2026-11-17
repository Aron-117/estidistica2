# Cómo abrir y compilar un proyecto con Git y Visual Studio Code

## 1. Instala las herramientas

- Instala [Git](https://git-scm.com/downloads).
- Instala [Visual Studio Code](https://code.visualstudio.com/).
- Instala también las herramientas necesarias para el lenguaje del proyecto (por ejemplo, Python, Node.js o .NET).

> Visual Studio Code es el editor. Git sirve para descargar y actualizar el código. Para compilar, necesitas las herramientas del lenguaje que use el proyecto.

## 2. Descarga el repositorio

1. En GitHub, abre el repositorio y copia su URL desde el botón **Code**.
2. En Visual Studio Code, abre la paleta de comandos con **Ctrl + Mayús + P**.
3. Busca y selecciona **Git: Clone**.
4. Pega la URL, elige una carpeta y selecciona **Open** cuando termine la descarga.

También puedes abrir la carpeta del repositorio desde **File > Open Folder**.

## 3. Compila el proyecto

1. En Visual Studio Code, abre **Terminal > New Terminal**.
2. Revisa las instrucciones del proyecto para encontrar el comando de compilación. Este depende del lenguaje y de los archivos del proyecto.
3. Ejecuta ese comando en la terminal. Si el proyecto incluye una tarea de compilación configurada, también puedes presionar **Ctrl + Mayús + B** y elegirla.

## 4. Actualiza el código

Para descargar cambios nuevos del repositorio, abre la terminal en la carpeta del proyecto y ejecuta:

```bash
git pull
```

## Importante para este repositorio

Actualmente este repositorio solo contiene este README; todavía no incluye código ni archivos de proyecto que se puedan compilar. Cuando agregues el proyecto, incluye aquí el comando de compilación específico de su lenguaje.
