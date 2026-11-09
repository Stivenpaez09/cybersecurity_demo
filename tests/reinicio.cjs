/* Verifica recuperación real tras terminar y volver a iniciar solo su propio proceso. */
const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const {once} = require('node:events');
const net = require('node:net');
const assert = require('node:assert/strict');

async function puertoLibre() {
  const servidor = net.createServer();
  servidor.listen(0, '127.0.0.1');
  await once(servidor, 'listening');
  const numero = servidor.address().port;
  await new Promise(resolver => servidor.close(resolver));
  return numero;
}

(async () => {
  const web = await puertoLibre(), modbus = await puertoLibre();
  const navegador = await chromium.launch({headless: true});
  const pagina = await navegador.newPage();
  let proceso, registro = '';
  function arrancar() {
    const codigo = `import app.config as c; c.PUERTO_WEB=${web}; c.PUERTO_MODBUS=${modbus}; from app.main import main; main()`;
    proceso = spawn(process.env.PYTHON_DEMO || '.venv/Scripts/python.exe', ['-c', codigo],
      {windowsHide: true, env: {...process.env, MODO: 'inseguro', DIRECCION_ESCUCHA: '127.0.0.1', PYTHONIOENCODING: 'utf-8'}});
    proceso.stderr.on('data', datos => registro += datos);
    proceso.stdout.on('data', datos => registro += datos);
  }
  async function detener() {
    if (proceso && proceso.exitCode === null && !proceso.killed) {
      const terminado = once(proceso, 'exit');
      proceso.kill();
      await terminado;
    }
  }
  try {
    arrancar();
    await pagina.goto(`http://localhost:${web}/ponente`, {waitUntil: 'domcontentloaded'}).catch(async () => {
      // El proceso puede tardar más que el primer intento de navegación.
      for (let intento = 0; intento < 40; intento++) {
        try { await pagina.goto(`http://localhost:${web}/ponente`); return; }
        catch (_) { await new Promise(resolver => setTimeout(resolver, 100)); }
      }
      throw new Error(`La planta no inició: ${registro}`);
    });
    await pagina.waitForFunction(() => /activa/i.test(document.querySelector('#conexion').textContent));
    await pagina.click('[data-modo="protegido"]');
    await pagina.waitForFunction(() => /protegido/i.test(document.querySelector('#modo').textContent));
    await detener();
    await pagina.waitForFunction(() => !document.querySelector('#aviso').hidden && document.querySelector('#aviso').textContent.includes('DESACTUALIZADOS'));
    arrancar();
    await pagina.waitForFunction(() => /activa/i.test(document.querySelector('#conexion').textContent) && /inseguro/i.test(document.querySelector('#modo').textContent));
    assert.equal(await pagina.locator('#valvula').textContent(), 'Cerrada');
    console.log('Reinicio real: pérdida de telemetría detectada, reconexión automática y estado inicial recuperado.');
  } finally { await detener(); await navegador.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
