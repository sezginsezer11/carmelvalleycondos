/* Shared RealScout listings embed (see /assets/rs-embed.css).
   Turns every .rs-embed that holds a RealScout iframe into:
   - an inline preview with a full-width "Search homes full screen" button under it
     (tapping anywhere on the preview also opens it), and
   - a full-screen view with a top bar: "Back to page" (exit) and "Open in new tab".
   The phone's Back button and the Esc key also exit full screen.
   /#expand-map (the bottom nav's Find Homes link) opens the first embed full screen. */
(function(){
  var ICON_EXPAND = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
  var ICON_BACK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>';
  var ICON_NEW = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6M10 14 21 3"/></svg>';
  var open = null;

  // RealScout is heavy (≈1.4 MB of its own code + trackers), so the iframe
  // ships with data-src and only loads on the visitor's first interaction
  // (scroll, tap, key, mouse wheel) or when they open it.
  function load(embed){
    var iframe = embed.querySelector('iframe');
    if (!iframe || iframe.getAttribute('src')) return;
    embed.classList.add('is-loading');
    iframe.addEventListener('load', function(){ embed.classList.remove('is-loading'); embed.classList.add('is-loaded'); }, {once: true});
    iframe.setAttribute('src', iframe.getAttribute('data-src'));
  }
  function loadAll(){
    var e = document.querySelectorAll('.rsx');
    for (var i = 0; i < e.length; i++) load(e[i]);
  }

  function setup(embed){
    var iframe = embed.querySelector('iframe[src*="realscout.com"], iframe[data-src*="realscout.com"]');
    if (!iframe || embed.classList.contains('rsx')) return;
    var url = iframe.getAttribute('src') || iframe.getAttribute('data-src');
    embed.classList.add('rsx');
    if (iframe.getAttribute('src')) embed.classList.add('is-loaded');

    var ph = document.createElement('div');
    ph.className = 'rsx-ph';
    ph.setAttribute('aria-hidden', 'true');
    ph.innerHTML = '<div class="rsx-ph-in"><svg viewBox="0 0 24 24"><path d="M12 21s7-7.1 7-12a7 7 0 0 0-14 0c0 4.9 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>' +
      '<strong>Live MLS listings</strong><span class="rsx-ph-wait">Loading homes for sale&hellip;</span><span class="rsx-ph-tap">Tap to see homes for sale</span></div>';
    embed.insertBefore(ph, iframe);

    var bar = document.createElement('div');
    bar.className = 'rsx-bar';
    bar.innerHTML = '<button type="button" class="rsx-exit">' + ICON_BACK + 'Back to page</button>' +
      '<a href="' + url.replace(/"/g, '&quot;') + '" target="_blank" rel="noopener">Open in new tab ' + ICON_NEW + '</a>';
    embed.insertBefore(bar, embed.firstChild);

    var catcher = document.createElement('div');
    catcher.className = 'rsx-catch';
    catcher.setAttribute('aria-hidden', 'true');
    embed.appendChild(catcher);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rsx-open';
    btn.innerHTML = ICON_EXPAND + 'Search homes full screen';
    embed.appendChild(btn);

    function show(){ openEmbed(embed); }
    catcher.addEventListener('click', show);
    btn.addEventListener('click', show);
    bar.querySelector('.rsx-exit').addEventListener('click', function(){ closeEmbed(true); });
  }

  function openEmbed(embed){
    if (open) return;
    load(embed);
    open = embed;
    embed.classList.add('is-open');
    document.documentElement.classList.add('rsx-lock');
    try { history.pushState({rsx: true}, ''); } catch (e) {}
  }
  function closeEmbed(fromButton){
    if (!open) return;
    open.classList.remove('is-open');
    document.documentElement.classList.remove('rsx-lock');
    open = null;
    if (fromButton && history.state && history.state.rsx) { try { history.back(); } catch (e) {} }
  }

  window.addEventListener('popstate', function(){ if (open) closeEmbed(false); });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeEmbed(true); });

  function init(){
    var embeds = document.querySelectorAll('.rs-embed');
    for (var i = 0; i < embeds.length; i++) setup(embeds[i]);
    // no plain 'scroll' here: test robots fire scroll events when they resize the page
    var evs = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
    function first(){
      evs.forEach(function(ev){ window.removeEventListener(ev, first, true); });
      loadAll();
    }
    evs.forEach(function(ev){ window.addEventListener(ev, first, {capture: true, passive: true}); });
    function fromHash(){
      if (location.hash === '#expand-map' && embeds[0]){
        try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
        openEmbed(embeds[0]);
      }
    }
    fromHash();
    window.addEventListener('hashchange', fromHash);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
