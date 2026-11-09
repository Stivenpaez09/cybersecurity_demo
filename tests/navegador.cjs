/* Prueba real de DOM: npm install, planta iniciada, npm run test:e2e. */
const {chromium} = require('playwright');
const {execFile} = require('node:child_process');
const {promisify} = require('node:util');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const ejecutar = promisify(execFile);

(async () => {
  const navegador = await chromium.launch({headless: true});
  const contexto = await navegador.newContext({viewport: {width: 1366, height: 768}});
  const pagina = await contexto.newPage();
  const base = `http://localhost:${Number(process.env.PUERTO_WEB_PRUEBA || 18473)}`;
  const externas = [], errores = [];
  pagina.on('request', solicitud => {
    if (!solicitud.url().startsWith(`${base}/`)) externas.push(solicitud.url());
  });
  pagina.on('pageerror', error => errores.push(error.message));
  const python = process.env.PYTHON_DEMO || '.venv/Scripts/python.exe';
  const cli = async (...argumentos) => {
    const ejecutable = process.env.DOCKER_DEMO === '1' ? 'docker' : python;
    const parametros = process.env.DOCKER_DEMO === '1'
      ? ['compose', 'exec', '-T', 'planta', 'python', ...argumentos] : argumentos;
    try { return await ejecutar(ejecutable, parametros, {env: {...process.env, PYTHONIOENCODING: 'utf-8'}}); }
    catch (error) { if (error.code === 2) return error; throw error; }
  };
  try {
    await pagina.goto(`${base}/`);
    await pagina.waitForFunction(() => /activa/i.test(document.querySelector('#conexion').textContent));
    assert.equal(await pagina.locator('button').count(), 0);
    const ponente = await contexto.newPage();
    await ponente.goto(`${base}/ponente`);
    await ponente.waitForSelector('[data-modo="inseguro"]');
    await ponente.click('[data-modo="inseguro"]');
    await ponente.waitForFunction(() => document.querySelector('#resultado-control').textContent.includes('aplicada'));
    // Una respuesta de polling retrasada no debe revertir un cambio de modo ya confirmado.
    let liberarConsulta, confirmarCaptura;
    const permisoRespuesta = new Promise(resolver => liberarConsulta = resolver);
    const consultaCapturada = new Promise(resolver => confirmarCaptura = resolver);
    await ponente.route('**/api/estado', async ruta => {
      const respuestaAntigua = await ruta.fetch();
      confirmarCaptura();
      await permisoRespuesta;
      await ruta.fulfill({response: respuestaAntigua});
    }, {times: 1});
    await consultaCapturada;
    await ponente.click('[data-modo="protegido"]');
    await ponente.waitForFunction(() => /protegido/i.test(document.querySelector('#modo').textContent));
    await ponente.evaluate(() => {
      window.modosObservados = [];
      window.observadorModo = new MutationObserver(() => window.modosObservados.push(document.querySelector('#modo').textContent));
      window.observadorModo.observe(document.querySelector('#modo'), {childList: true, subtree: true});
    });
    liberarConsulta();
    await ponente.waitForTimeout(700);
    assert(!(await ponente.evaluate(() => window.modosObservados)).some(modo => /inseguro/i.test(modo)));
    await ponente.evaluate(() => window.observadorModo.disconnect());
    await ponente.click('[data-modo="inseguro"]');
    await pagina.waitForFunction(() => /inseguro/i.test(document.querySelector('#modo').textContent));
    const latencias = [];
    const escenarios = ['abrir-valvula', 'temperatura-alta', 'presion-alta'];
    for (let indice = 0; indice < 20; indice++) {
      const generacionAnterior = await pagina.locator('body').getAttribute('data-generacion');
      await ponente.click('#reiniciar');
      await pagina.waitForFunction(anterior => document.body.dataset.generacion !== anterior, generacionAnterior);
      const escenario = escenarios[indice % escenarios.length];
      const inicio = performance.now();
      await cli('cliente_control.py', escenario);
      await pagina.waitForFunction(orden => orden === 'abrir-valvula'
        ? document.querySelector('#valvula').textContent === 'Abierta'
        : Number(document.querySelector(orden === 'temperatura-alta' ? '#temperatura' : '#presion').textContent) > (orden === 'temperatura-alta' ? 60 : 2.3),
        escenario, {timeout: 1800});
      latencias.push(performance.now() - inicio);
      assert(latencias.at(-1) < 2000, 'Reacción visible debe ser < 2 s');
    }
    // Captura coherente del primer escenario para comparar las dos resoluciones.
    await ponente.click('#reiniciar');
    await cli('cliente_control.py', 'abrir-valvula');
    await pagina.waitForFunction(() => document.querySelector('#valvula').textContent === 'Abierta');
    fs.mkdirSync('artifacts', {recursive: true});
    for (const [ancho, alto] of [[1366,768], [1920,1080]]) {
      await pagina.setViewportSize({width: ancho, height: alto});
      await pagina.screenshot({path: `artifacts/tablero-${ancho}.png`, fullPage: true});
      assert(await pagina.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      assert(await pagina.evaluate(() => document.querySelector('footer').getBoundingClientRect().bottom <= innerHeight));
    }
    await ponente.click('#reiniciar');
    await ponente.click('[data-modo="protegido"]');
    await pagina.waitForFunction(() => /protegido/i.test(document.querySelector('#modo').textContent));
    const rechazo = await cli('cliente_control.py', 'abrir-valvula');
    assert.equal(rechazo.code, 2);
    await pagina.waitForFunction(() => document.querySelector('#eventos').textContent.includes('Escritura rechazada'));
    assert.equal(await pagina.locator('#valvula').textContent(), 'Cerrada');
    await cli('cliente_autorizado.py', 'abrir-valvula');
    await pagina.waitForFunction(() => document.querySelector('#valvula').textContent === 'Abierta');
    assert(!(await pagina.locator('#estado-valvula').textContent()).toLowerCase().includes('indebida'));
    await pagina.screenshot({path: 'artifacts/tablero-protegido.png', fullPage: true});
    await contexto.setOffline(true);
    await pagina.waitForFunction(() => !document.querySelector('#aviso').hidden && document.querySelector('#aviso').textContent.includes('DESACTUALIZADOS'));
    await contexto.setOffline(false);
    await pagina.waitForFunction(() => /activa/i.test(document.querySelector('#conexion').textContent));
    assert.deepEqual(externas, []);
    assert.deepEqual(errores, []);
    const informe = {entorno: process.env.DOCKER_DEMO === '1' ? 'docker' : 'nativo',
      mediciones: latencias.length, escenarios, maximo_ms: Math.max(...latencias), externas, errores,
      resoluciones: ['1366x768', '1920x1080'], rechazo_modbus: true, gateway: true, reconexion: true,
      respuesta_atrasada_descartada: true};
    fs.writeFileSync('artifacts/navegador.json', JSON.stringify(informe, null, 2));
    fs.writeFileSync(`artifacts/navegador-${informe.entorno}.json`, JSON.stringify(informe, null, 2));
    console.log(JSON.stringify(informe, null, 2));
  } finally { await navegador.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
