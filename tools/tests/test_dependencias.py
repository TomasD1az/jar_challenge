import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verificar_dependencias import (  # noqa: E402
    cargar_lista, dependencias_ros, normalizar_pip, permitida_ros, revisar)

RAIZ = Path(__file__).resolve().parents[2]
LISTA = RAIZ / 'tools' / 'dependencias_permitidas.yaml'

PACKAGE = """<?xml version="1.0"?>
<package format="3">
  <name>equipo_jar</name>
  <version>0.1.0</version>
  <description>x</description>
  <maintainer email="a@b.c">x</maintainer>
  <license>MIT</license>
  {dependencias}
  <export><build_type>ament_python</build_type></export>
</package>
"""


def entrega(tmp_path, dependencias, requirements=''):
    """Arma una carpeta con src/equipo_jar/package.xml y requirements.txt; devuelve (src, requirements)."""
    pkg = tmp_path / 'src' / 'equipo_jar'
    pkg.mkdir(parents=True)
    (pkg / 'package.xml').write_text(PACKAGE.format(dependencias=dependencias))
    req = tmp_path / 'requirements.txt'
    req.write_text(requirements)
    return tmp_path / 'src', req


def test_el_template_cumple_su_propia_lista():
    assert revisar(LISTA, RAIZ / 'src', RAIZ / 'requirements.txt') == []


def test_acepta_deteccion_con_opencv(tmp_path):
    src, req = entrega(tmp_path, '<exec_depend>cv_bridge</exec_depend>'
                       '<exec_depend>python3-opencv</exec_depend><test_depend>python3-pytest</test_depend>')
    assert revisar(LISTA, src, req) == []


def test_rechaza_una_dependencia_de_ros_fuera_de_la_lista(tmp_path):
    src, req = entrega(tmp_path, '<exec_depend>rclpy</exec_depend><exec_depend>nav2_bringup</exec_depend>')
    errores = revisar(LISTA, src, req)
    assert len(errores) == 1 and 'nav2_bringup' in errores[0]


def test_mira_todas_las_etiquetas(tmp_path):
    src, req = entrega(tmp_path, '<depend>x_a</depend><build_depend>x_b</build_depend>'
                       '<test_depend>x_c</test_depend><buildtool_depend>x_d</buildtool_depend>')
    assert len(revisar(LISTA, src, req)) == 4


def test_los_paquetes_de_ament_vienen_con_ros(tmp_path):
    src, req = entrega(tmp_path, '<buildtool_depend>ament_cmake</buildtool_depend>'
                       '<test_depend>ament_flake8</test_depend>')
    assert revisar(LISTA, src, req) == []


def test_rechaza_un_paquete_de_pip_que_no_esta(tmp_path):
    src, req = entrega(tmp_path, '', 'torch==2.3.0\n')
    errores = revisar(LISTA, src, req)
    assert len(errores) == 1 and 'torch' in errores[0]


def test_rechaza_opciones_y_urls_en_requirements(tmp_path):
    src, req = entrega(tmp_path, '', '--extra-index-url https://x.org/simple\n'
                       'paquete @ git+https://github.com/x/y.git\n')
    assert len(revisar(LISTA, src, req)) == 2


def test_requirements_solo_con_comentarios_esta_bien(tmp_path):
    src, req = entrega(tmp_path, '', '# nada\n\n   # tampoco\n')
    assert revisar(LISTA, src, req) == []


def test_sin_requirements_esta_bien(tmp_path):
    src, req = entrega(tmp_path, '')
    req.unlink()
    assert revisar(LISTA, src, req) == []


def test_pip_acepta_lo_que_la_lista_permita(tmp_path):
    lista = tmp_path / 'lista.yaml'
    lista.write_text('ros: []\npip: [Scikit_Learn]\n')
    src, req = entrega(tmp_path, '', 'scikit-learn==1.4.0\nscikit.learn>=1\nnumpy\n')
    errores = revisar(lista, src, req)
    assert len(errores) == 1 and 'numpy' in errores[0]


def test_revisa_cada_paquete_de_src(tmp_path):
    src, req = entrega(tmp_path, '<exec_depend>rclpy</exec_depend>')
    otro = src / 'otro'
    otro.mkdir()
    (otro / 'package.xml').write_text(PACKAGE.format(dependencias='<exec_depend>raro</exec_depend>'))
    errores = revisar(LISTA, src, req)
    assert len(errores) == 1 and 'raro' in errores[0]


def test_nombres_de_pip_y_patrones():
    assert normalizar_pip('Scikit_Learn.X') == 'scikit-learn-x'
    assert permitida_ros('ament_flake8', ['ament_*'])
    assert not permitida_ros('ros_ament', ['ament_*'])
    assert cargar_lista(LISTA)[1] == []


def test_dependencias_ros_sin_repetir(tmp_path):
    src, _ = entrega(tmp_path, '<exec_depend>rclpy</exec_depend><depend>rclpy</depend>')
    assert dependencias_ros(src / 'equipo_jar' / 'package.xml') == ['rclpy']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-q']))
