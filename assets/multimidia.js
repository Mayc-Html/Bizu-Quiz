/* BizuQuiz: trilhas, efeitos e créditos animados. */
(() => {
  'use strict';
  const script = document.currentScript;
  if (!script || !document.body) return;
  const root = new URL('../', script.src);
  const files = {
    menu: "Naruto - Konohamaru's Theme (128 kbps).mp3",
    quiz: 'Bully - Walk Theme - [Music] (HD)(MP3_320K).mp3',
    credits: 'musicas para fim de video gameplay.mp3',
    easter: 'WhatsApp Audio 2026-07-14 at 11.04.58 (1).mpeg',
    start: 'okay-lets-go_buBmJye (2).mp3',
    fail: 'Fail 1.mp3',
    win: 'victory_sJDDywi.mp3',
    surprise: '23- Gota.mp3'
  };
  const read = (k) => { try { return sessionStorage.getItem(k); } catch (_) { return null; } };
  const save = (k, v) => { try { sessionStorage.setItem(k, v); } catch (_) {} };
  const src = (key) => new URL('songs/' + encodeURIComponent(files[key]), root).href;
  const track = script.dataset.track || 'menu';
  const cue = script.dataset.effect || '';
  const bg = new Audio(src(track));
  bg.loop = true;
  bg.preload = 'metadata';
  bg.volume = 0.4;
  const effect = cue ? new Audio(src(cue)) : null;
  if (effect) { effect.preload = 'auto'; effect.volume = 0.65; }
  let cueDone = !effect;
  let enabled = read('bizu-sound-off') !== '1';
  let pending = false;
  const control = document.createElement('button');
  control.type = 'button';
  control.className = 'bizu-sound-toggle';
  function update() {
    const playing = enabled && (!bg.paused || (effect && !effect.paused && !cueDone));
    control.textContent = playing ? '🔊' : '🔇';
    const label = playing ? 'Pausar som' : 'Ativar som';
    control.setAttribute('aria-label', label);
    control.title = label;
  }
  function remember() {
    if (bg.currentTime > 0 && Number.isFinite(bg.currentTime)) {
      save('bizu-track-position-' + track, String(bg.currentTime));
    }
  }
  bg.addEventListener('loadedmetadata', () => {
    const previous = Number(read('bizu-track-position-' + track));
    if (Number.isFinite(previous) && previous > 0 && previous < bg.duration) {
      try { bg.currentTime = previous; } catch (_) {}
    }
  }, {once: true});
  window.addEventListener('pagehide', remember);
  bg.addEventListener('timeupdate', () => { if (Math.floor(bg.currentTime) % 3 === 0) remember(); });
  function play() {
    if (!enabled || pending || document.hidden) return;
    const player = cueDone ? bg : effect;
    if (!player || !player.paused) { update(); return; }
    pending = true;
    try {
      Promise.resolve(player.play()).catch(() => {}).finally(() => {
        pending = false;
        if (!enabled) player.pause();
        update();
        if (cueDone && player === effect && enabled) play();
      });
    } catch (_) { pending = false; update(); }
  }
  if (effect) {
    const finish = () => { cueDone = true; play(); };
    effect.addEventListener('ended', finish, {once: true});
    effect.addEventListener('error', finish, {once: true});
    effect.addEventListener('play', update);
    effect.addEventListener('pause', update);
  }
  bg.addEventListener('play', update);
  bg.addEventListener('pause', update);
  control.addEventListener('click', () => {
    const playing = !bg.paused || (effect && !effect.paused && !cueDone);
    if (playing || (enabled && pending)) {
      enabled = false;
      save('bizu-sound-off', '1');
      bg.pause();
      if (effect) effect.pause();
      remember();
    } else {
      enabled = true;
      save('bizu-sound-off', '0');
      play();
    }
    update();
  });
  const retry = (event) => {
    if (event.target === control || control.contains(event.target)) return;
    play();
  };
  document.addEventListener('pointerup', retry, true);
  document.addEventListener('keydown', retry, true);
  window.addEventListener('pageshow', play);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) play(); });
  document.body.append(control);
  update();
  play();

  if (!document.body.classList.contains('bizu-credits')) return;
  const video = document.getElementById('meuVideo');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let running = !reduced.matches;
  let frame = 0, last = 0, target = window.scrollY;
  const speed = 42; // pixels por segundo, sem depender da taxa de atualização
  const scrollButton = document.createElement('button');
  scrollButton.className = 'bizu-scroll-toggle';
  scrollButton.type = 'button';
  function refresh() {
    scrollButton.textContent = running ? 'Pausar rolagem' : 'Continuar rolagem';
  }
  function pause() {
    running = false;
    cancelAnimationFrame(frame);
    frame = 0;
    refresh();
  }
  function tick(now) {
    if (!running) return;
    if (!last) last = now;
    const elapsed = Math.min(now - last, 50) / 1000;
    last = now;
    const bottom = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    target = Math.min(bottom, target + speed * elapsed);
    window.scrollTo(0, target);
    if (target >= bottom - 1) { pause(); return; }
    frame = requestAnimationFrame(tick);
  }
  function resume() {
    if (running && frame) return;
    running = true;
    target = window.scrollY;
    last = 0;
    refresh();
    frame = requestAnimationFrame(tick);
  }
  scrollButton.addEventListener('click', () => running ? pause() : resume());
  const back = document.querySelector('.botao-voltar');
  if (back) back.insertAdjacentElement('afterend', scrollButton);
  else document.body.prepend(scrollButton);
  refresh();
  window.addEventListener('wheel', pause, {passive: true});
  window.addEventListener('touchstart', (e) => { if (e.target !== scrollButton) pause(); }, {passive: true});
  document.addEventListener('keydown', (e) => {
    if (['Tab', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(e.key) && e.target !== scrollButton) pause();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  if (video) {
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.playsInline = true;
    if (!reduced.matches) {
      video.autoplay = true;
      video.play().catch(() => {});
    }
  }
  function onMotion() {
    if (reduced.matches) { pause(); if (video) { video.autoplay = false; video.pause(); } }
  }
  if (reduced.addEventListener) reduced.addEventListener('change', onMotion);
  if (running) {
    // Aguarda a mídia/metadados e o layout, sem bloquear se a mídia falhar.
    if (document.readyState === 'complete') resume();
    else window.addEventListener('load', () => { if (running) resume(); }, {once: true});
  }
})();
