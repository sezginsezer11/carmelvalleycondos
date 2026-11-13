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

  function setup(embed){
    var iframe = embed.querySelector('iframe[src*="realscout.com"]');
    if (!iframe || embed.classList.contains('rsx')) return;
    var url = iframe.getAttribute('src');
    embed.classList.add('rsx');

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
