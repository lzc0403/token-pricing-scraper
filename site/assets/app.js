
const SITE_DATA = __SITE_DATA__;
const PEAK = __PEAK_DATA__;
(function(){
  var state = {
    rate: 7.0,
    models: {},     // canonical model -> bool （全部大模型）
    channels: {}    // source id -> bool
  };

  function fmt(n){
    if (n == null || isNaN(n)) return '—';
    if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
    return (Math.round(n * 1000) / 1000).toString();
  }

  var totop = document.getElementById('toTop');
  if (totop){
    window.addEventListener('scroll', function(){
      totop.classList.toggle('is-show', window.scrollY > 500);
    }, {passive:true});
    totop.addEventListener('click', function(){ window.scrollTo({top:0,behavior:'smooth'}); });
  }

  document.querySelectorAll('.market-tab').forEach(function(tab){
    tab.addEventListener('click', function(){
      var m = tab.dataset.market;
      document.querySelectorAll('.market-tab').forEach(function(t){
        var on = t === tab;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      ['domestic','overseas'].forEach(function(key){
        var p = document.getElementById('panel-' + key);
        if (!p) return;
        var show = key === m;
        p.hidden = !show;
        p.classList.toggle('is-active', show);
      });
      updateVisibleCount();
    });
  });

  document.querySelectorAll('th.sortable').forEach(function(th){
    th.addEventListener('click', function(){
      var table = th.closest('table');
      var tbody = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.js-row'));
      var key = th.dataset.key;
      var idx = Array.prototype.indexOf.call(th.parentNode.children, th);
      var asc = th.getAttribute('aria-sort') !== 'ascending';
      th.parentNode.querySelectorAll('th[aria-sort]').forEach(function(t){ if (t!==th) t.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
      rows.sort(function(a,b){
        if (key==='model'||key==='canon'||key==='source'){
          var av=(a.cells[idx].dataset.sort||a.cells[idx].textContent||'').trim();
          var bv=(b.cells[idx].dataset.sort||b.cells[idx].textContent||'').trim();
          return asc ? av.localeCompare(bv,'zh') : bv.localeCompare(av,'zh');
        }
        var an=parseFloat(a.cells[idx].dataset.sort), bn=parseFloat(b.cells[idx].dataset.sort);
        if (isNaN(an)) an = asc ? Infinity : -Infinity;
        if (isNaN(bn)) bn = asc ? Infinity : -Infinity;
        return asc ? an-bn : bn-an;
      });
      rows.forEach(function(r){ tbody.appendChild(r); });
    });
  });

  var meta = SITE_DATA.filter_meta || {};
  var allModels = meta.models || meta.all_models || SITE_DATA.canons || [];
  var channels = meta.channels || [];
  allModels.forEach(function(m){ state.models[m] = true; });
  channels.forEach(function(c){ state.channels[c.id] = true; });

  function selectedKeys(map){
    return Object.keys(map).filter(function(k){ return map[k]; });
  }
  function allOn(map){
    var ks = Object.keys(map);
    return ks.length && ks.every(function(k){ return map[k]; });
  }

  function renderChips(){
    var mBox = document.getElementById('modelChips');
    var cBox = document.getElementById('channelChips');
    if (mBox){
      mBox.innerHTML = allModels.map(function(m){
        return '<button type="button" class="chip'+(state.models[m]?' is-on':'')+'" data-kind="model" data-id="'+m+'">'+m+'</button>';
      }).join('') || '<span class="rate-hint">无模型数据</span>';
    }
    if (cBox){
      cBox.innerHTML = channels.map(function(c){
        return '<button type="button" class="chip'+(state.channels[c.id]?' is-on':'')+'" data-kind="channel" data-id="'+c.id+'">'+(c.label||c.id)+'</button>';
      }).join('');
    }
  }

  function rowMatches(row){
    var canon = row.getAttribute('data-canonical') || '';
    var source = row.getAttribute('data-source') || '';
    if (!state.models[canon]) return false;
    if (!state.channels[source]) return false;
    return true;
  }

  function updatePrices(){
    var rate = state.rate;
    document.querySelectorAll('tr.js-row').forEach(function(row){
      var cur = (row.getAttribute('data-currency') || '').toUpperCase();
      var input = parseFloat(row.getAttribute('data-input'));
      var output = parseFloat(row.getAttribute('data-output'));
      var inputRmb = parseFloat(row.getAttribute('data-input-rmb'));
      var outputRmb = parseFloat(row.getAttribute('data-output-rmb'));
      if (cur === 'USD'){
        var inHint = row.querySelector('.js-rmb-hint[data-side="input"]');
        var outHint = row.querySelector('.js-rmb-hint[data-side="output"]');
        if (inHint){
          var v = isNaN(input) ? null : input * rate;
          inHint.textContent = v == null ? '约 ¥—' : ('约 ¥' + fmt(v));
        }
        if (outHint){
          var v2 = isNaN(output) ? null : output * rate;
          outHint.textContent = v2 == null ? '约 ¥—' : ('约 ¥' + fmt(v2));
        }
      } else {
        var inMain = row.querySelector('.js-cny-main[data-side="input"]');
        var outMain = row.querySelector('.js-cny-main[data-side="output"]');
        if (inMain && !isNaN(inputRmb)) inMain.textContent = fmt(inputRmb);
        if (outMain && !isNaN(outputRmb)) outMain.textContent = fmt(outputRmb);
      }
    });
  }

  function applyFilter(){
    var shown = 0;
    document.querySelectorAll('tr.js-row').forEach(function(row){
      var ok = rowMatches(row);
      row.classList.toggle('is-hidden', !ok);
      if (ok) shown += 1;
    });
    document.querySelectorAll('.price-table').forEach(function(table){
      var wrap = table.closest('.table-wrap');
      if (!wrap) return;
      var rows = table.querySelectorAll('tr.js-row');
      var visible = table.querySelectorAll('tr.js-row:not(.is-hidden)');
      var empty = wrap.querySelector('.empty-filter');
      if (!empty){
        empty = document.createElement('div');
        empty.className = 'empty-filter';
        empty.textContent = '当前筛选条件下无匹配数据，请调整模型分类或渠道选择。';
        wrap.appendChild(empty);
      }
      empty.classList.toggle('is-show', rows.length > 0 && visible.length === 0);
    });
    updateSummary();
    updateVisibleCount(shown);
    maybeSyncChart();
    updateConfirmButton();
  }

  function updateSummary(){
    var mSel = selectedKeys(state.models);
    var chSel = selectedKeys(state.channels);
    var mText = allOn(state.models) ? '全部模型' : (mSel.length ? mSel.join(' / ') : '无模型');
    var chText = allOn(state.channels) ? '全部渠道' : (chSel.length ? chSel.map(function(id){
      var hit = channels.find(function(c){ return c.id === id; });
      return hit ? hit.label : id;
    }).join(' / ') : '无渠道');
    var el = document.getElementById('filterSummary');
    if (el) el.textContent = '当前：' + mText + ' · ' + chText + ' · 汇率 ' + state.rate.toFixed(2);
  }

  function updateVisibleCount(shown){
    if (typeof shown !== 'number'){
      shown = document.querySelectorAll('tr.js-row:not(.is-hidden)').length;
    }
    var el = document.getElementById('visibleCount');
    if (el) el.textContent = '显示 ' + shown + ' 行';
    var metricRate = document.getElementById('metricRate');
    if (metricRate) metricRate.innerHTML = state.rate.toFixed(2) + '<small>¥/$</small>';
    var fxCur = document.getElementById('fxCurrent');
    if (fxCur) fxCur.textContent = state.rate.toFixed(2);
  }

  function bindChips(){
    document.querySelectorAll('.chip').forEach(function(chip){
      chip.addEventListener('click', function(){
        var kind = chip.dataset.kind;
        var id = chip.dataset.id;
        if (kind === 'model'){
          state.models[id] = !state.models[id];
        } else if (kind === 'channel'){
          state.channels[id] = !state.channels[id];
        }
        chip.classList.toggle('is-on');
        applyFilter();
      });
    });
    document.querySelectorAll('.linkish').forEach(function(btn){
      btn.addEventListener('click', function(){
        var scope = btn.dataset.scope;
        var act = btn.dataset.act;
        if (scope === 'model'){
          if (act === 'all'){
            Object.keys(state.models).forEach(function(k){ state.models[k] = true; });
          } else if (act === 'none'){
            Object.keys(state.models).forEach(function(k){ state.models[k] = false; });
          } else if (act === 'domestic'){
            var domestic = (meta.domestic_models || []);
            var dset = {};
            domestic.forEach(function(m){ dset[m] = true; });
            Object.keys(state.models).forEach(function(k){ state.models[k] = !!dset[k]; });
          } else if (act === 'overseas'){
            var overseas = (meta.overseas_models || []);
            var oset = {};
            overseas.forEach(function(m){ oset[m] = true; });
            Object.keys(state.models).forEach(function(k){ state.models[k] = !!oset[k]; });
          }
        } else if (scope === 'channel'){
          Object.keys(state.channels).forEach(function(k){ state.channels[k] = act === 'all'; });
        }
        renderChips();
        bindChips();
        applyFilter();
      });
    });
  }


  // FIX 3: Model card → render 4-dim detail panel & scroll to it
  function escHtml(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function fmtNum(v){
    if (v == null || isNaN(v)) return '';
    if (Math.abs(v - Math.round(v)) < 1e-9) return String(Math.round(v));
    return (Math.round(v * 10000) / 10000).toString();
  }
  function priceCell(v, cur){
    if (v == null || v === '') return '<td class="num na">—</td>';
    return '<td class="num">' + fmtNum(v) + (cur ? ' <span class="unit-hint">' + escHtml(cur) + '</span>' : '') + '</td>';
  }
  function cacheWriteCell(row){
    // Anthropic 5m/1h 双档；其余单值 cache_write
    if (row.cache_write_5m != null || row.cache_write_1h != null){
      var s = '';
      if (row.cache_write_5m != null) s += '5m ' + fmtNum(row.cache_write_5m);
      if (row.cache_write_1h != null) s += (s ? ' / ' : '') + '1h ' + fmtNum(row.cache_write_1h);
      return '<td class="num">' + s + '</td>';
    }
    if (row.cache_write != null) return '<td class="num">' + fmtNum(row.cache_write) + '</td>';
    return '<td class="num na">—</td>';
  }
  function renderModelDetail(canonical){
    var body = document.getElementById('detailBody');
    var sec = document.getElementById('model-detail');
    if (!body) return;
    if (!canonical){
      body.innerHTML = '<div class="detail-empty">👈 请选择上方一张模型卡片，查看它的完整 4 维分档报价</div>';
      return;
    }
    var info = (SITE_DATA.model_details || {})[canonical];
    if (!info || !info.rows || !info.rows.length){
      body.innerHTML = '<div class="detail-empty">暂无「' + escHtml(canonical) + '」的报价明细。</div>';
      return;
    }
    var rowHtml = info.rows.map(function(row){
      var officialCls = (row.source && /deepseek|bigmodel|kimi|minimax|volcengine|openai|anthropic|gemini|grok|aliyun$|tencent$/.test(String(row.source))) ? ' row-official' : '';
      var srcLbl = escHtml(row.source_label || row.source || '—');
      var tier = escHtml(row.tier || '');
      var cur = escHtml(row.currency || '');
      var ctx = escHtml(row.context || '—');
      var srcCell = row.tier
        ? '<td><span class="row-src">' + srcLbl + '</span><br>' + tier + '</td>'
        : '<td><span class="row-src">' + srcLbl + '</span></td>';
      var storage = row.cache_storage != null
        ? '<td class="num">' + fmtNum(row.cache_storage) + ' <span class="unit-hint">/1M·h</span></td>'
        : '<td class="num na">—</td>';
      return '<tr class="' + officialCls.trim() + '">' +
        srcCell +
        priceCell(row.input, cur) +
        priceCell(row.output, cur) +
        cacheWriteCell(row) +
        priceCell(row.cache_hit, cur) +
        storage +
        '<td>' + ctx + '</td>' +
        '<td>' + cur + '</td>' +
        '</tr>';
    }).join('');
    var head = '<tr><th>来源 / 档位</th><th>输入</th><th>输出</th><th>缓存创建</th><th>缓存读取</th><th>缓存存储</th><th>上下文</th><th>币种</th></tr>';
    var cur0 = (info.rows[0] || {}).currency || '';
    var changes = (SITE_DATA.official_changes || {}).changes || [];
    var chList = changes.filter(function(ch){ return ch.canonical === canonical; });
    var changeBadge = '';
    if (chList.length){
      var c0 = chList[0];
      var pctTxt = '';
      if (c0.pct != null && !isNaN(c0.pct)){
        var fp = Number(c0.pct);
        pctTxt = (fp > 0 ? ' +' : ' ') + Math.round(fp) + '%';
      }
      changeBadge = '<span class="detail-alert-badge" title="' + escHtml((c0.date || '')) + '">📈 官方调价' + escHtml(pctTxt) + '</span>';
    }
    body.innerHTML =
      '<div class="detail-head">' +
        '<span class="detail-title-badge">' + escHtml(canonical) + '</span>' +
        (changeBadge) +
        '<span class="detail-vendor">官方价 + 渠道对照 · ' + escHtml(cur0) + ' / 1M tokens</span>' +
      '</div>' +
      '<div class="detail-table-wrap"><table class="detail-table">' +
        '<thead>' + head + '</thead><tbody>' + rowHtml + '</tbody>' +
      '</table></div>' +
      '<p class="detail-note"><b>单位说明</b>：输入/输出/缓存创建/缓存读取 = $ 或 ¥ / 1M tokens；缓存存储（Gemini）= $ / 1M tokens / 小时。' +
      'Anthropic 缓存创建分 5m（1.25× 输入）与 1h（2× 输入）两档；OpenAI 长档缓存创建官网前端注入，抓取不到记 —。' +
      '官方价 = 定价锚点；渠道价为转售挂牌，仅供参考。</p>';
    if (sec) sec.scrollIntoView({behavior:'smooth', block:'start'});
  }
  function bindDetailDismiss(){
    var btn = document.getElementById('detailDismiss');
    if (btn) btn.addEventListener('click', function(){ renderModelDetail(''); });
  }

  // FIX 2: Click model card → scroll to channel panel, switch tab, highlight row
  function scrollToChannelPanel(canonical){
    // 优先按模型卡片国籍选择面板：国内模型→domestic，海外模型→overseas
    var card = document.querySelector('.model-pick[data-canonical="' + canonical + '"]');
    var preferredPanel = card ? (card.getAttribute('data-region') || '') : '';
    if (preferredPanel !== 'domestic' && preferredPanel !== 'overseas') preferredPanel = '';

    var targetRow = null;
    var targetPanel = null;

    // Step 1: 若有国籍偏好，先在对应面板找匹配行
    if (preferredPanel){
      var panel = document.getElementById('panel-' + preferredPanel);
      if (panel){
        var row = panel.querySelector('tr.js-row[data-canonical="' + canonical + '"]');
        if (row){ targetRow = row; targetPanel = preferredPanel; }
      }
    }

    // Step 2: 无偏好或没找到，遍历两个面板兜底
    if (!targetPanel){
      ['domestic','overseas'].forEach(function(market){
        if (market === preferredPanel) return; // 已试过
        var panel = document.getElementById('panel-' + market);
        if (!panel) return;
        var row = panel.querySelector('tr.js-row[data-canonical="' + canonical + '"]');
        if (row){ targetRow = row; targetPanel = market; }
      });
    }
    if (!targetPanel){
      // Fallback: scroll to first channel block
      var block = document.querySelector('.block-channel');
      if (block) block.scrollIntoView({behavior:'smooth', block:'start'});
      return;
    }
    // Switch to the correct tab
    var tab = document.querySelector('.market-tab[data-market="' + targetPanel + '"]');
    if (tab && !tab.classList.contains('is-active')){
      tab.click();
    }
    // Wait a tick for tab to render then scroll + highlight
    setTimeout(function(){
      // Re-find row in case DOM changed
      var panel = document.getElementById('panel-' + targetPanel);
      var row = panel ? panel.querySelector('tr.js-row[data-canonical="' + canonical + '"]') : null;
      if (!row) return;
      row.scrollIntoView({behavior:'smooth', block:'center'});
      // Briefly highlight the row
      row.classList.add('row-hl');
      setTimeout(function(){ row.classList.remove('row-hl'); }, 2000);
    }, 250);
  }

  function selectOnlyModel(canonical){
    Object.keys(state.models).forEach(function(key){ state.models[key] = key === canonical; });
    renderChips();
    bindChips();
    applyFilter();
    // 桌面端：折叠侧边栏；移动端：关闭抽屉
    if (window.matchMedia('(min-width:1025px)').matches){
      if (!isCollapsed && typeof toggleSidebarLayout === 'function') toggleSidebarLayout();
    } else {
      if (typeof closeSidebar === 'function') closeSidebar();
    }
    // FIX 3: 渲染模型详情面板（4 维分档报价）并滚动到位；不再强制跳渠道区
    if (typeof renderModelDetail === 'function') renderModelDetail(canonical);
  }

  function bindPriceAlertClose(){
    var closeBtn = document.getElementById('priceAlertClose');
    if (!closeBtn) return;
    closeBtn.addEventListener('click', function(){
      var bar = document.getElementById('priceAlert');
      if (bar) bar.style.display = 'none';
    });
  }

  function bindModelCards(){
    bindPriceAlertClose();
    document.querySelectorAll('.model-pick[data-canonical]').forEach(function(card){
      if (card.getAttribute('data-bound') === '1') return;
      card.setAttribute('data-bound','1');
      card.addEventListener('click', function(){
        selectOnlyModel(card.dataset.canonical);
      });
      card.addEventListener('keydown', function(e){
        if (e.key === 'Enter' || e.key === ' '){
          e.preventDefault();
          selectOnlyModel(card.dataset.canonical);
        }
      });
    });
  }
  bindModelCards();

  // 移动端侧边栏展开/收起
  var sidebarToggle = document.getElementById('sidebarToggle');
  var sidebar = document.getElementById('sidebar');
  var sidebarBackdrop = document.getElementById('sidebarBackdrop');
  var sidebarClose = document.getElementById('sidebarClose');
  function openSidebar(){
    if (sidebar) sidebar.classList.add('is-open');
    if (sidebarBackdrop) sidebarBackdrop.classList.add('is-open');
  }
  function closeSidebar(){
    if (sidebar) sidebar.classList.remove('is-open');
    if (sidebarBackdrop) sidebarBackdrop.classList.remove('is-open');
  }
  if (sidebarToggle) sidebarToggle.addEventListener('click', function(){
    // 按钮在侧边栏内部：桌面端切换折叠，移动端关闭浮层
    if (layout && window.innerWidth > 1024) {
      toggleSidebarLayout();
    } else {
      closeSidebar();
    }
  });
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
  if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);

  // 卡片聚光描边 + 轻微 3D 倾斜（尊重 prefers-reduced-motion）
  (function(){
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var cards = document.querySelectorAll('.model-pick');
    var MAX = 5; // 最大倾斜角度
    cards.forEach(function(card){
      card.addEventListener('pointermove', function(e){
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
        card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
        card.style.setProperty('--ry', ((px - 0.5) * MAX * 2).toFixed(2) + 'deg');
        card.style.setProperty('--rx', ((0.5 - py) * MAX * 2).toFixed(2) + 'deg');
      });
      card.addEventListener('pointerleave', function(){
        card.style.setProperty('--ry', '0deg');
        card.style.setProperty('--rx', '0deg');
      });
    });
  })();


  // 桌面端折叠/展开侧边栏（FIX 3: 增加 hover-peek + 自动收起）
  var layout = document.querySelector('.layout');
  var sidebarCollapse = document.getElementById('sidebarCollapse');
  var sidebarReopen = document.getElementById('sidebarReopen');
  var sidebarWarmupTimer = null;
  var sidebarLeaveTimer = null;
  var isCollapsed = false;
  var isPeek = false;

  function clearSidebarTimers(){
    if (sidebarWarmupTimer){ clearTimeout(sidebarWarmupTimer); sidebarWarmupTimer = null; }
    if (sidebarLeaveTimer){ clearTimeout(sidebarLeaveTimer); sidebarLeaveTimer = null; }
  }

  function collapseSidebar(){
    if (!layout || isCollapsed) return;
    isCollapsed = true;
    layout.classList.add('is-collapsed');
    sidebarReopen.classList.add('is-show');
    isPeek = false;
  }
  function expandSidebar(){
    if (!layout || !isCollapsed) return;
    isCollapsed = false;
    layout.classList.remove('is-collapsed');
    sidebarReopen.classList.remove('is-show');
    isPeek = false;
  }
  function toggleSidebarLayout(){
    if (!layout) return;
    if (isCollapsed) expandSidebar(); else collapseSidebar();
  }

  // Hover-peek: hover reopen button → temporarily expand; leave → collapse
  if (sidebarReopen){
    sidebarReopen.addEventListener('mouseenter', function(){
      if (!isCollapsed) return;
      clearSidebarTimers();
      isPeek = true;
      layout.classList.remove('is-collapsed');
      sidebar.classList.add('is-peek');
    });
    sidebarReopen.addEventListener('mouseleave', function(){
      if (!isPeek) return;
      clearSidebarTimers();
      sidebarLeaveTimer = setTimeout(function(){
        if (isCollapsed && isPeek){
          layout.classList.add('is-collapsed');
          sidebar.classList.remove('is-peek');
          isPeek = false;
        }
      }, 800);
    });
  }
  // When peeking, moving into sidebar keeps it open
  if (sidebar){
    sidebar.addEventListener('mouseenter', function(){
      if (isPeek){ clearSidebarTimers(); }
    });
    sidebar.addEventListener('mouseleave', function(){
      if (!isPeek || !isCollapsed) return;
      clearSidebarTimers();
      sidebarLeaveTimer = setTimeout(function(){
        if (isCollapsed && isPeek){
          layout.classList.add('is-collapsed');
          sidebar.classList.remove('is-peek');
          isPeek = false;
        }
      }, 600);
    });
  }

  if (sidebarCollapse) sidebarCollapse.addEventListener('click', toggleSidebarLayout);
  if (sidebarReopen) sidebarReopen.addEventListener('click', function(){
    // click fully toggles (cancel peek state)
    isPeek = false;
    clearSidebarTimers();
    toggleSidebarLayout();
  });

  // 确认按钮：有选中内容时显示，点击后收起侧边栏
  var sidebarConfirm = document.getElementById('sidebarConfirm');
  function isDefaultFilter(){
    return allOn(state.models) && allOn(state.channels) && Math.abs(state.rate - 7.0) < 0.01;
  }
  function updateConfirmButton(){
    if (!sidebarConfirm) return;
    sidebarConfirm.classList.toggle('is-show', !isDefaultFilter());
  }
  if (sidebarConfirm){
    sidebarConfirm.addEventListener('click', function(){
      closeSidebar();
      document.getElementById('main').scrollIntoView({behavior:'smooth', block:'start'});
    });
  }

  var fx = document.getElementById('fxRate');
  var fxReset = document.getElementById('fxReset');
  function setRate(v){
    var n = parseFloat(v);
    if (isNaN(n) || n <= 0) n = 7.0;
    if (n > 100) n = 100;
    state.rate = Math.round(n * 100) / 100;
    if (fx) fx.value = state.rate;
    updatePrices();
    applyFilter();
  }
  if (fx){
    fx.addEventListener('change', function(){ setRate(fx.value); });
    fx.addEventListener('input', function(){
      var n = parseFloat(fx.value);
      if (!isNaN(n) && n > 0) {
        state.rate = Math.round(n * 100) / 100;
        updatePrices();
        updateSummary();
        updateVisibleCount();
        updateConfirmButton();
      }
    });
  }
  if (fxReset) fxReset.addEventListener('click', function(){ setRate(7.0); });
  var filterReset = document.getElementById('filterReset');
  if (filterReset){
    filterReset.addEventListener('click', function(){
      Object.keys(state.models).forEach(function(k){ state.models[k]=true; });
      Object.keys(state.channels).forEach(function(k){ state.channels[k]=true; });
      renderChips();
      bindChips();
      setRate(7.0);
    });
  }

  var btn = document.getElementById('btnExcel');
  if (btn){
    btn.addEventListener('click', function(){
      if (typeof XLSX === 'undefined'){ alert('Excel 组件未加载，请联网后重试。'); return; }
      btn.disabled = true;
      try{
        var rows = [['区块','模型分组','模型','来源','输入','输出','输入¥(当前汇率)','输出¥(当前汇率)','缓存','上下文','货币','官方','最低']];
        function push(kind, list){
          (list||[]).forEach(function(r){
            if (!state.models[r.canonical]) return;
            if (!state.channels[r.source]) return;
            var inRmb = r.input_rmb, outRmb = r.output_rmb;
            if ((r.currency||'').toUpperCase()==='USD'){
              inRmb = r.input == null ? null : r.input * state.rate;
              outRmb = r.output == null ? null : r.output * state.rate;
            }
            rows.push([
              kind, r.canonical||'', r.model||r.model_raw||'', r.source_label||r.source||'',
              r.input==null?'':r.input, r.output==null?'':r.output,
              inRmb==null?'':Math.round(inRmb*1000)/1000, outRmb==null?'':Math.round(outRmb*1000)/1000,
              r.cache_hit==null?'':r.cache_hit, r.context||'', r.currency||'',
              r.is_official?'是':'否', r.is_lowest?'是':'否'
            ]);
          });
        }
        push('官网原价', SITE_DATA.official_rows);
        push('海外主流', SITE_DATA.overseas_rows);
        push('国内渠道', SITE_DATA.channel_domestic);
        push('海外渠道', SITE_DATA.channel_overseas);
        // 主流模型目录（国内/海外双专区）
        function pushMainstream(region, vendors){
          (vendors||[]).forEach(function(vendor){
            (vendor.models||[]).forEach(function(model){
              var tier = (model.pricing && model.pricing.tiers && model.pricing.tiers[0]) || {};
              rows.push([
                region, vendor.name||vendor.id||'', model.display_name||model.canonical||'',
                model.source_label||vendor.source_id||vendor.id||'',
                tier.input_price==null?'':tier.input_price,
                tier.output_price==null?'':tier.output_price,
                '', '',
                tier.cache_input_price==null?'':tier.cache_input_price,
                model.context_label||'', model.currency||'',
                '是', ''
              ]);
            });
          });
        }
        if (SITE_DATA.mainstream_sections){
          pushMainstream('国内主流', SITE_DATA.mainstream_sections.domestic);
          pushMainstream('海外主流', SITE_DATA.mainstream_sections.overseas);
        }
        var ws = XLSX.utils.aoa_to_sheet(rows);
        var wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, '比价');
        var stamp = (SITE_DATA.generated_at||'').replace(/[: ]/g,'-').slice(0,19);
        XLSX.writeFile(wb, 'token-pricing-'+stamp+'.xlsx');
      } finally { btn.disabled=false; }
    });
  }

  var chart = null, metric = 'input';
  var COLORS = { primary:'#4f46e5', green:'#059669', muted:'#cbd5e1' };
  var sel = document.getElementById('modelSelect');
  var canvas = document.getElementById('priceChart');
  function getRows(c){ return (SITE_DATA.chart && SITE_DATA.chart[c]) || []; }
  function valOf(r){
    if (metric==='output'){
      if ((r.currency||'').toUpperCase()==='USD' && r.output != null) return r.output * state.rate;
      return r.output_rmb;
    }
    if ((r.currency||'').toUpperCase()==='USD' && r.input != null) return r.input * state.rate;
    return r.input_rmb;
  }
  function draw(canon){
    if (typeof Chart === 'undefined' || !canvas) return;
    var rows = getRows(canon).filter(function(r){
      return state.channels[r.source] !== false && state.models[canon] !== false;
    });
    if (state.models[canon] === false) rows = [];
    var vals = rows.map(function(r){ var v=valOf(r); return v==null?null:v; });
    var nums = vals.filter(function(v){ return v!=null; });
    var min = nums.length ? Math.min.apply(null, nums) : null;
    var colors = vals.map(function(v){ return (v!=null && min!=null && v===min) ? COLORS.green : COLORS.primary; });
    var ctx = canvas.getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type:'bar',
      data:{
        labels: rows.map(function(r){ return (r.source_label||r.source) + (r.model?(' · '+r.model):''); }),
        datasets:[{ label: metric==='output'?'输出价':'输入价', data:vals, backgroundColor:colors, borderRadius:6, maxBarThickness:48 }]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label:function(c){ return c.parsed.y==null?'无数据':'¥ '+fmt(c.parsed.y); } } } },
        scales:{
          y:{ beginAtZero:true, ticks:{ callback:function(v){ return '¥'+v; }, color:'#64748b' }, grid:{ color:'#eef2f7' } },
          x:{ grid:{ display:false }, ticks:{ color:'#64748b', maxRotation:45, minRotation:0 } }
        }
      }
    });
  }
  function maybeSyncChart(){
    if (!sel) return;
    var mSel = selectedKeys(state.models);
    if (mSel.length === 1){
      for (var i=0;i<sel.options.length;i++){
        if (sel.options[i].value === mSel[0]){ sel.value = mSel[0]; break; }
      }
    }
    draw(sel.value);
  }
  if (sel){
    sel.addEventListener('change', function(e){ draw(e.target.value); });
    document.querySelectorAll('.seg-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        metric = btn.dataset.metric;
        document.querySelectorAll('.seg-btn').forEach(function(b){
          var on = b.dataset.metric===metric;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on?'true':'false');
        });
        draw(sel.value);
      });
    });
  }

  renderChips();
  bindChips();
  setRate(7.0);
  if (sel) draw(sel.value);
})();

/* ===== 历史价格趋势图 ===== */
(function(){
  var HIST = (SITE_DATA && SITE_DATA.history) || {};
  var dates = HIST.dates || [];
  var series = HIST.series || {};
  if (dates.length < 2) return;  // 不足 2 点不渲染（HTML 已显示占位）

  var trendMetric = 'input';
  var COLOR_POOL = ['#4f46e5','#059669','#dc2626','#d97706','#7c3aed','#0891b2','#db2777','#65a30d','#ea580c','#0d9488'];
  var tSel = document.getElementById('trendModelSelect');
  var tCanvas = document.getElementById('trendChart');
  if (!tSel || !tCanvas) return;

  function valOf(rec){
    if (!rec) return null;
    if (trendMetric === 'output'){
      if ((rec.currency||'').toUpperCase() === 'USD' && rec.output != null) return rec.output * state.rate;
      return rec.output_rmb != null ? rec.output_rmb : rec.output;
    }
    if ((rec.currency||'').toUpperCase() === 'USD' && rec.input != null) return rec.input * state.rate;
    return rec.input_rmb != null ? rec.input_rmb : rec.input;
  }

  function drawTrend(canon){
    if (typeof Chart === 'undefined') return;
    var srcMap = series[canon] || {};
    var srcIds = Object.keys(srcMap);
    // 过滤：被取消勾选的渠道不显示
    srcIds = srcIds.filter(function(s){ return state.channels[s] !== false; });
    if (srcIds.length === 0) srcIds = Object.keys(srcMap);  // fallback 全显示

    var datasets = srcIds.map(function(src, i){
      var pts = dates.map(function(d){
        var rec = (srcMap[src] || {})[d];
        var v = valOf(rec);
        return v == null ? null : v;
      });
      var label = (SITE_DATA.filter_meta && SITE_DATA.filter_meta.channels || [])
        .filter(function(c){ return c.id === src; })[0];
      label = label ? label.label : src;
      return {
        label: label,
        data: pts,
        borderColor: COLOR_POOL[i % COLOR_POOL.length],
        backgroundColor: COLOR_POOL[i % COLOR_POOL.length],
        spanGaps: true,
        tension: 0.3,
        pointRadius: 2,
        borderWidth: 2
      };
    });

    if (window.__trendChart) window.__trendChart.destroy();
    var ctx = tCanvas.getContext('2d');
    window.__trendChart = new Chart(ctx, {
      type: 'line',
      data: { labels: dates, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true, position: 'bottom', labels: { color: '#475569', boxWidth: 12, font: { size: 11 } } },
          tooltip: { callbacks: { label: function(c){ return c.dataset.label + ': ¥' + fmt(c.parsed.y); } } }
        },
        scales: {
          y: { beginAtZero: true, ticks: { callback: function(v){ return '¥' + v; }, color: '#64748b' }, grid: { color: '#eef2f7' } },
          x: { grid: { display: false }, ticks: { color: '#64748b', maxRotation: 45, minRotation: 0 } }
        }
      }
    });
  }

  if (tSel){
    tSel.addEventListener('change', function(e){ drawTrend(e.target.value); });
    document.querySelectorAll('[data-trend-metric]').forEach(function(btn){
      btn.addEventListener('click', function(){
        trendMetric = btn.dataset.trendMetric;
        document.querySelectorAll('[data-trend-metric]').forEach(function(b){
          var on = b.dataset.trendMetric === trendMetric;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        drawTrend(tSel.value);
      });
    });
    drawTrend(tSel.value);
  }
})();

/* ===== 峰谷动态比价时钟 ===== */
(function(){
  if (typeof PEAK === 'undefined' || !PEAK.schedules) return;
  var SCHEDS = PEAK.schedules;

  // 当前北京时间（UTC+8），与各方窗口同基准
  function bjNow(){
    var n = new Date();
    var utc = n.getTime() + n.getTimezoneOffset() * 60000;
    return new Date(utc + 8 * 3600000);
  }
  function hourFloat(d){ return d.getHours() + d.getMinutes() / 60; }
  // 返回 'peak' | 'off'：peak/off 只定义其一，另一为补集
  // weekend_off=true（DeepSeek 官方）：周六(6)/周日(0) 全天按空闲档计
  function periodOf(sched, d){
    var h = hourFloat(d);
    if (sched.weekend_off){
      var wd = d.getDay();
      if (wd === 6 || wd === 0) return 'off';
    }
    if (sched.peak){
      for (var i=0;i<sched.peak.length;i++){ var a=sched.peak[i][0],b=sched.peak[i][1]; if (h>=a && h<b) return 'peak'; }
      return 'off';
    }
    if (sched.off){
      for (var i=0;i<sched.off.length;i++){ var a=sched.off[i][0],b=sched.off[i][1]; if (h>=a && h<b) return 'off'; }
      return 'peak';
    }
    return 'off';
  }
  function presentScheds(){
    var seen = {'deepseek_official': true};
    document.querySelectorAll('.js-row[data-sched]').forEach(function(tr){
      var s = tr.getAttribute('data-sched');
      if (s) seen[s] = true;
    });
    return seen;
  }
  function who(k){
    if (k === 'deepseek_official') return 'DeepSeek 官方';
    if (k === 'aliyun_intl') return '阿里云国际站';
    return k;
  }
  function recalc(){
    var bj = bjNow();
    var hh = ('0' + bj.getHours()).slice(-2);
    var mm = ('0' + bj.getMinutes()).slice(-2);
    var ofPer = periodOf(SCHEDS.deepseek_official, bj);

    // 顶部时钟：各方当前档位
    var clock = document.getElementById('peak-clock');
    if (clock){
      var html = '<span class="pc-time">🕐 北京时间 ' + hh + ':' + mm + '</span>';
      html += '<span class="pc-sep">·</span>';
      var seen = presentScheds();
      Object.keys(seen).forEach(function(k){
        var sc = SCHEDS[k]; if (!sc) return;
        var p = periodOf(sc, bj);
        var isPeak = (p === 'peak');
        var label = isPeak ? sc.peak_label : sc.off_label;
        html += '<span class="pc-pill ' + (isPeak ? 'peak' : 'off') + '">' + who(k) + '：' + label + '</span>';
      });
      html += '<span class="pc-sep">比价随当前时段实时切换</span>';
      clock.innerHTML = html;
    }

    // 溢价单元格：按官方当前档位 + 渠道自身当前档位实时计算
    document.querySelectorAll('.js-row[data-ch-off]').forEach(function(tr){
      var chOff = parseFloat(tr.getAttribute('data-ch-off'));
      var chPeakRaw = tr.getAttribute('data-ch-peak');
      var chPeak = chPeakRaw ? parseFloat(chPeakRaw) : null;
      var ofOff = parseFloat(tr.getAttribute('data-of-off'));
      var ofPeakRaw = tr.getAttribute('data-of-peak');
      var ofPeak = ofPeakRaw ? parseFloat(ofPeakRaw) : null;
      var schedKey = tr.getAttribute('data-sched');
      var chSched = schedKey ? SCHEDS[schedKey] : null;
      var chPer = chSched ? periodOf(chSched, bj) : 'flat';

      var chPrice = (chPer === 'peak' && chPeak != null) ? chPeak : chOff;
      var ofPrice = (ofPer === 'peak' && ofPeak != null) ? ofPeak : ofOff;

      var tag = tr.querySelector('.js-premium');
      if (tag && chPrice != null && ofPrice && ofPrice > 0){
        var prem = (chPrice - ofPrice) / ofPrice * 100;
        var sign = prem >= 0 ? '+' : '';
        tag.textContent = sign + prem.toFixed(1) + '%';
        var chTxt = chPer === 'peak' ? '忙/高' : (chPer === 'off' ? '闲/低' : '平');
        var ofTxt = ofPer === 'peak' ? '忙/高' : '闲/低';
        tag.title = '当前比价基准：渠道(' + chTxt + ') vs 官方(' + ofTxt + ')';
        tag.classList.toggle('is-peak', ofPer === 'peak');
        tag.classList.toggle('is-off', ofPer === 'off');
      }
    });
  }
  recalc();
  setInterval(recalc, 60000);
})();
