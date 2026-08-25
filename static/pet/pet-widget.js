/* ============================================================
 * 鲸鱼娘 AI 宠物助手 (pet-widget.js)
 * 外观来自 DeepSeek-Balance-Whale-Widget (DSH 小鲸鱼余额挂件)
 * 功能：透明立绘 / 悬浮拖拽 + 左右吸附镜像 / 点击Q弹 + 弹气泡 /
 *       悬浮显示当前页面信息 / 博客数据播报 / 登录状态感知 /
 *       气泡对话(规则+RAG+可选DeepSeek) / 日夜心情
 * ============================================================ */
(function () {
  if (window.__petWhaleLoaded) return
  window.__petWhaleLoaded = true

  var BASE = '/static/pet/'
  var IMG_WHALE = BASE + 'DSniang1.png'
  var SND_PRESS = BASE + 'Ya1.mp3'
  var SND_RELEASE = BASE + 'Ya2.mp3'

  var SIZE = 150            // 鲸鱼显示尺寸
  var CLICK_SQ = 9          // 拖拽判定阈值（平方距离）
  var SQUISH = 'scaleY(.88) scaleX(1.05)'  // 原插件按压变形

  /* ---------- 台词池（日夜心情） ---------- */
  var LINES = {
    morning: [
      '早上好呀！新的一天也要加油哦~ (๑•̀ㅂ•́)و✧',
      '早~ 昨晚睡得好吗？我一直在看着博客呢！',
      '清晨的第一缕阳光，送给正在写博客的你 ☀️',
    ],
    day: [
      '摸鱼时间到！要不要看看站内有什么新文章？',
      '今天的博客数据也很棒呢，继续保持！',
      '嘿嘿，我一直在这里看着你写代码哦~',
    ],
    evening: [
      '晚上好呀~ 一天辛苦啦！',
      '夜深了还在写博客，真是勤劳的作者！',
      '写完这章就休息一下吧，身体要紧！',
    ],
    night: [
      '都这么晚了，还不睡吗？熬夜写代码可不好哦~',
      '夜深人静，最适合静下心写文章了呢……',
      'Zzz…… 我陪你一起熬夜！',
    ],
  }
  var GREETING = {
    morning: '早上好',
    day: '下午好',
    evening: '晚上好',
    night: '夜深了',
  }

  function getPeriod() {
    var h = new Date().getHours()
    if (h >= 5 && h < 11) return 'morning'
    if (h >= 11 && h < 18) return 'day'
    if (h >= 18 && h < 23) return 'evening'
    return 'night'
  }

  function pickOne(arr) { return arr[Math.floor(Math.random() * arr.length)] }
  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)) }

  /* ---------- 注入样式 ---------- */
  var style = document.createElement('style')
  style.textContent =
    /* 容器：绝对定位用 left/top，镜像翻转不影响布局 */
    '#pet-whale-root{position:fixed;left:auto;top:auto;right:auto;bottom:auto;z-index:2147483000;' +
    'width:' + SIZE + 'px;height:' + SIZE + 'px;cursor:grab;touch-action:none;' +
    'font-family:"Microsoft YaHei","PingFang SC",sans-serif;user-select:none;-webkit-user-select:none;' +
    'transition:left .3s cubic-bezier(.2,.8,.3,1.1),top .3s cubic-bezier(.2,.8,.3,1.1),transform .3s ease}' +
    /* 透明立绘：无白底无圆角无阴影 */
    '#pet-whale-root .pet-whale-img{position:absolute;left:0;top:0;width:100%;height:100%;' +
    'object-fit:contain;pointer-events:none;transform-origin:center bottom;' +
    'transition:transform .12s ease}' +
    '#pet-whale-root.pet-pressed .pet-whale-img{transform:' + SQUISH + '}' +
    /* 左吸附：只翻转鲸鱼立绘（文本框保持正常方向） */
    '#pet-whale-root.pet-left .pet-whale-img{transform:scaleX(-1)}' +
    '#pet-whale-root.pet-left.pet-pressed .pet-whale-img{transform:scaleX(-1) ' + SQUISH + '}' +
    /* 气泡 */
    '#pet-whale-root .pet-bubble{position:absolute;left:50%;bottom:calc(100% + 10px);' +
    'transform:translateX(-50%);width:280px;max-width:80vw;background:#fff;' +
    'border:2px solid #203170;border-radius:18px;box-shadow:0 8px 24px rgba(32,49,112,.3);' +
    'padding:12px 14px;display:none;z-index:6;font-size:13px;color:#333;line-height:1.6;' +
    'text-align:left;cursor:default}' +
    '#pet-whale-root.pet-above .pet-bubble{top:calc(100% + 10px);bottom:auto}' +
    '#pet-whale-root.pet-above .pet-bubble:after{top:-11px;bottom:auto;' +
    'transform:translateX(-50%) rotate(225deg)}' +
    /* 左吸附时气泡移到鲸鱼右侧，避免溢出屏幕左缘 */
    '#pet-whale-root.pet-left .pet-bubble{left:calc(100% + 12px);bottom:auto;top:50%;' +
    'transform:translateY(-50%);max-width:calc(60vw)}' +
    '#pet-whale-root.pet-left .pet-bubble:after{left:-11px;bottom:auto;top:50%;' +
    'transform:translateY(-50%) rotate(135deg)}' +
    '#pet-whale-root .pet-bubble:after{content:"";position:absolute;left:50%;bottom:-11px;' +
    'width:16px;height:16px;background:#fff;border-right:2px solid #203170;' +
    'border-bottom:2px solid #203170;transform:translateX(-50%) rotate(45deg);' +
    'border-radius:2px}' +
    '#pet-whale-root .pet-bubble .pet-b-text{margin-bottom:6px;white-space:pre-wrap;word-break:break-word;' +
    'max-height:160px;overflow-y:auto}' +
    '#pet-whale-root .pet-bubble .pet-b-hits{margin:4px 0;padding-top:6px;border-top:1px dashed #c9d2ee;' +
    'font-size:12px;color:#4a6bb8}' +
    '#pet-whale-root .pet-bubble .pet-b-hits a{color:#4a6bb8;text-decoration:none;display:block;' +
    'padding:1px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '#pet-whale-root .pet-bubble .pet-b-hits a:hover{text-decoration:underline}' +
    '#pet-whale-root .pet-chat-row{display:flex;gap:6px;margin-top:8px}' +
    '#pet-whale-root .pet-chat-row input{flex:1;min-width:0;border:1px solid #c9d2ee;border-radius:8px;' +
    'padding:5px 8px;font-size:12px;outline:none;background:#fff;color:#333}' +
    '#pet-whale-root .pet-chat-row input:focus{border-color:#203170}' +
    '#pet-whale-root .pet-chat-row button{border:none;background:#203170;color:#fff;border-radius:8px;' +
    'padding:5px 10px;font-size:12px;cursor:pointer}' +
    '#pet-whale-root .pet-chat-row button:hover{background:#2c3f8f}' +
    '#pet-whale-root .pet-bubble.pet-show{display:block;animation:petBubbleIn .22s ease}' +
    '@keyframes petBubbleIn{from{opacity:0;transform:translateX(-50%) translateY(8px) scale(.94)}' +
    'to{opacity:1;transform:translateX(-50%) translateY(0) scale(1)}}' +
    '#pet-whale-root.pet-left .pet-bubble.pet-show{animation:petBubbleInL .22s ease}' +
    '@keyframes petBubbleInL{from{opacity:0;transform:translateY(-50%) translateY(8px) scale(.94)}' +
    'to{opacity:1;transform:translateY(-50%) translateY(0) scale(1)}}'

  document.head.appendChild(style)

  /* ---------- 构建 DOM ---------- */
  var root = document.createElement('div')
  root.id = 'pet-whale-root'

  var img = document.createElement('img')
  img.className = 'pet-whale-img'
  img.src = IMG_WHALE
  img.alt = '鲸鱼娘'
  img.draggable = false

  var bubble = document.createElement('div')
  bubble.className = 'pet-bubble'
  var bText = document.createElement('div')
  bText.className = 'pet-b-text'
  var bHits = document.createElement('div')
  bHits.className = 'pet-b-hits'
  var chatRow = document.createElement('div')
  chatRow.className = 'pet-chat-row'
  var chatInput = document.createElement('input')
  chatInput.type = 'text'
  chatInput.placeholder = '问问鲸鱼娘…'
  chatInput.maxLength = 200
  var chatBtn = document.createElement('button')
  chatBtn.textContent = '发送'
  chatRow.appendChild(chatInput)
  chatRow.appendChild(chatBtn)
  bubble.appendChild(bText)
  bubble.appendChild(bHits)
  bubble.appendChild(chatRow)

  root.appendChild(img)
  root.appendChild(bubble)
  document.body.appendChild(root)

  /* ---------- 状态 ---------- */
  var state = {
    h: null,        // 'left' | 'right' | null（自由）
    hOff: 0,        // 距左/右的距离
    v: null,        // 'top' | 'bottom' | null
    vOff: 0,
    left: 0,
    top: 0,
    bubbleShown: false,
    bubbleTimer: null,
    bubbleSource: null,   // 'hover' | 'click'
    posKey: 'pet_whale_pos_v2',
    pageStats: null,
    chatHistory: [],      // 历史对话 [{role:'user'|'ai', text}]
    inputFocused: false,  // 输入框是否聚焦（聚焦时不自动隐藏）
  }
  var CHAT_HISTORY_MAX = 30   // 历史对话最多保留条数

  /* ---------- 位置模型（同原插件：始终用 left/top 表达） ---------- */
  function viewport() {
    return { w: window.innerWidth, h: window.innerHeight }
  }

  function express() {
    root.style.left = state.left + 'px'
    root.style.top = state.top + 'px'
    root.classList.toggle('pet-left', state.h === 'left')
    // 吸附在顶部时气泡改到下方
    root.classList.toggle('pet-above', state.v === 'top')
  }

  function settle() {
    var vp = viewport()
    var w = root.offsetWidth || SIZE
    var h = root.offsetHeight || SIZE
    var left = state.left, top = state.top
    var centerX = left + w / 2, centerY = top + h / 2
    var moved = false
    if (centerX < vp.w / 4) {
      state.h = 'left'
      state.hOff = 0
      left = 0
      moved = true
    } else if (centerX > vp.w * 3 / 4) {
      state.h = 'right'
      state.hOff = 0
      left = vp.w - w
      moved = true
    } else {
      state.h = null
      state.hOff = left
    }
    if (centerY < vp.h / 4) {
      state.v = 'top'
      state.vOff = 0
      top = 0
      moved = true
    } else if (centerY > vp.h * 3 / 4) {
      state.v = 'bottom'
      state.vOff = 0
      top = vp.h - h
      moved = true
    } else {
      state.v = null
      state.vOff = top
    }
    state.left = clamp(left, 0, Math.max(0, vp.w - w))
    state.top = clamp(top, 0, Math.max(0, vp.h - h))
    express()
    savePos()
    return moved
  }

  /* ---------- 位置记忆 ---------- */
  function savePos() {
    try {
      localStorage.setItem(state.posKey, JSON.stringify({
        h: state.h, hOff: state.hOff, v: state.v, vOff: state.vOff,
      }))
    } catch (e) { /* ignore */ }
  }

  function loadPos() {
    try {
      var s = JSON.parse(localStorage.getItem(state.posKey) || 'null')
      var vp = viewport()
      var w = root.offsetWidth || SIZE
      var h = root.offsetHeight || SIZE
      if (!s) {
        // 首次加载：默认右下角吸附
        state.h = 'right'
        state.hOff = 0
        state.left = Math.max(0, vp.w - w - 24)
        state.v = 'bottom'
        state.vOff = 0
        state.top = Math.max(0, vp.h - h - 24)
        express()
        savePos()
        return
      }
      if (s.h === 'left') { state.h = 'left'; state.hOff = 0; state.left = 0 }
      else if (s.h === 'right') { state.h = 'right'; state.hOff = 0; state.left = vp.w - w }
      else { state.h = null; state.hOff = s.hOff; state.left = clamp(s.hOff || 0, 0, Math.max(0, vp.w - w)) }
      if (s.v === 'top') { state.v = 'top'; state.vOff = 0; state.top = 0 }
      else if (s.v === 'bottom') { state.v = 'bottom'; state.vOff = 0; state.top = vp.h - h }
      else { state.v = null; state.vOff = s.vOff; state.top = clamp(s.vOff || 0, 0, Math.max(0, vp.h - h)) }
      express()
    } catch (e) {
      state.h = 'right'
      state.v = 'bottom'
      settle()
    }
  }

  window.addEventListener('resize', function () {
    // 吸附中的鲸鱼保持贴边，自由的按距离重算
    if (state.h === 'left') state.left = 0
    else if (state.h === 'right') state.left = Math.max(0, viewport().w - (root.offsetWidth || SIZE))
    if (state.v === 'top') state.top = 0
    else if (state.v === 'bottom') state.top = Math.max(0, viewport().h - (root.offsetHeight || SIZE))
    express()
  })

  /* ---------- 音效 ---------- */
  function playSound(src) {
    try {
      var a = new Audio(src)
      a.volume = 0.7
      var p = a.play()
      if (p && p.catch) p.catch(function () {})
    } catch (e) { /* ignore */ }
  }

  /* ---------- 拖拽 / 点击 / Q弹 ---------- */
  var drag = null

  function startDrag(x, y) {
    var rect = root.getBoundingClientRect()
    drag = {
      startX: x, startY: y,
      origLeft: rect.left, origTop: rect.top,
      w: rect.width, h: rect.height,
      moved: false,
    }
    root.classList.add('pet-pressed')
    playSound(SND_PRESS)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('touchmove', onMove, { passive: true })
    window.addEventListener('touchend', onUp)
  }

  function onMove(e) {
    if (!drag) return
    var x = e.touches ? e.touches[0].clientX : e.clientX
    var y = e.touches ? e.touches[0].clientY : e.clientY
    var dx = x - drag.startX
    var dy = y - drag.startY
    if (dx * dx + dy * dy >= CLICK_SQ) drag.moved = true
    var vp = viewport()
    state.left = clamp(drag.origLeft + dx, 0, Math.max(0, vp.w - drag.w))
    state.top = clamp(drag.origTop + dy, 0, Math.max(0, vp.h - drag.h))
    // 拖拽时禁止过渡动画
    root.style.transition = 'none'
    express()
  }

  function onUp(e) {
    if (!drag) return
    var wasMoved = drag.moved
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    window.removeEventListener('touchmove', onMove)
    window.removeEventListener('touchend', onUp)
    drag = null
    root.classList.remove('pet-pressed')
    root.style.transition = ''
    playSound(SND_RELEASE)
    if (wasMoved) {
      settle()
    } else {
      // 未移动 = 点击：弹对话框
      handleClick()
    }
  }

  root.addEventListener('mousedown', function (e) {
    if (e.button !== 0) return
    // 点击气泡内部：放行（让输入框能聚焦、按钮/链接可点），不启动拖拽
    if (e.target.closest && e.target.closest('.pet-bubble')) return
    e.preventDefault()
    startDrag(e.clientX, e.clientY)
  })
  root.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) return
    // 点击气泡内部：放行
    if (e.target.closest && e.target.closest('.pet-bubble')) return
    startDrag(e.touches[0].clientX, e.touches[0].clientY)
  }, { passive: true })

  /* ---------- 气泡 ---------- */
  function showBubble(text, hits, asHtml, source) {
    if (asHtml) {
      bText.innerHTML = text || ''
    } else {
      bText.textContent = text || ''
    }
    bHits.innerHTML = ''
    if (hits && hits.length) {
      hits.forEach(function (h) {
        var a = document.createElement('a')
        a.href = h.url
        a.target = '_blank'
        a.textContent = '📄 ' + h.title
        bHits.appendChild(a)
      })
    }
    bubble.classList.add('pet-show')
    state.bubbleShown = true
    state.bubbleSource = source || 'click'
    resetBubbleTimer()
  }

  function hideBubble() {
    // 输入框聚焦时不允许隐藏（避免打字过程中气泡消失）
    if (state.inputFocused) return
    bubble.classList.remove('pet-show')
    state.bubbleShown = false
    state.bubbleSource = null
    if (state.bubbleTimer) { clearTimeout(state.bubbleTimer); state.bubbleTimer = null }
  }

  function resetBubbleTimer() {
    if (state.bubbleTimer) { clearTimeout(state.bubbleTimer); state.bubbleTimer = null }
    // 输入聚焦时不启动自动隐藏计时器
    if (state.inputFocused) return
    // 只有 hover 预览模式才自动收起（8 秒）；
    // 点击打开的对话/统计/历史内容永不自动消失，仅通过点击空白处关闭
    if (state.bubbleSource !== 'hover') return
    state.bubbleTimer = setTimeout(hideBubble, 8000)
  }

  /* ---------- 当前页面信息（hover 显示） ---------- */
  // 固定路由前缀：这些路径段不是用户名
  var KNOWN_ROUTES = ['home', 'login', 'register', 'logout', 'backend', 'admin', 'pet', 'static', 'media',
    'get_code', 'set_password', 'up_or_down', 'comment', 'edit_user', 'add_article', 'add_category',
    'add_tag', 'edit', 'delete', 'favicon.ico']

  // 根据当前 URL 判断所在站点用户名（如 /feibi/、/feibi/article/7 → 'feibi'）
  function currentSiteUser() {
    var segs = (location.pathname || '').split('/').filter(Boolean)
    if (!segs.length) return ''
    var first = segs[0]
    if (KNOWN_ROUTES.indexOf(first) !== -1) return ''
    if (!/^\w+$/.test(first)) return ''
    return first
  }

  // 判断当前是否在文章详情页：/用户名/article/数字
  function currentArticleId() {
    var segs = (location.pathname || '').split('/').filter(Boolean)
    if (segs.length >= 3 && segs[1] === 'article' && /^\d+$/.test(segs[2])) {
      return segs[2]
    }
    return ''
  }

  function statsUrl() {
    var aid = currentArticleId()
    if (aid) return '/pet/stats/?article=' + aid
    var u = currentSiteUser()
    return u ? '/pet/stats/?blog=' + encodeURIComponent(u) : '/pet/stats/'
  }

  function pageInfoText() {
    var lines = []
    lines.push('📄 当前页面：' + (document.title || '未知'))
    lines.push('📍 ' + location.pathname)
    if (state.pageStats) {
      lines.push('')
      var as = state.pageStats.article_stats
      if (as) {
        // 文章详情页：显示当前文章数据
        lines.push('📌 当前文章：' + as.title)
        lines.push('👍 点赞 ' + as.up + '　👎 点踩 ' + as.down)
        lines.push('👀 阅读 ' + as.read + '　💬 评论 ' + as.comment)
      } else {
        var bs = state.pageStats.blog_stats
        if (bs) {
          // 命中站点：显示该站点汇总
          lines.push('🏠 ' + (bs.site_title || bs.blog) + ' 站点数据：')
          lines.push('📝 文章 ' + bs.stats.total + ' 篇')
          lines.push('👀 总阅读 ' + bs.stats.read)
          lines.push('👍 总点赞 ' + bs.stats.up + '　💬 总评论 ' + bs.stats.comment)
        } else {
          // 全站
          lines.push('📊 博客全站数据：')
          lines.push('📝 文章 ' + state.pageStats.stats.total + ' 篇')
          lines.push('👀 总阅读 ' + state.pageStats.stats.read)
          lines.push('👍 总点赞 ' + state.pageStats.stats.up + '　💬 总评论 ' + state.pageStats.stats.comment)
        }
      }
    }
    lines.push('')
    lines.push('（点击我聊天 · 按住可拖动）')
    return lines.join('\n')
  }

  function showPageInfo() {
    if (state.bubbleShown) return
    showBubble(pageInfoText(), null, false, 'hover')
    if (!state.pageStats) {
      fetch(statsUrl(), { credentials: 'same-origin' })
        .then(function (r) { return r.json() })
        .then(function (d) {
          if (d.ok) state.pageStats = d
          if (state.bubbleShown && state.bubbleSource === 'hover') {
            showBubble(pageInfoText(), null, false, 'hover')
          }
        })
        .catch(function () { /* ignore */ })
    }
  }

  /* ---------- 点击主逻辑 ---------- */
  function handleClick() {
    if (state.bubbleShown) {
      // 已显示：切到随机台词
      state.mode = 'random'
      showBubble(pickOne(LINES[getPeriod()]), null, false, 'click')
      return
    }
    // 有历史对话时：优先显示历史记录（方便继续聊）
    if (state.chatHistory.length) {
      state.mode = 'history'
      showBubble('📝 历史对话：\n' + renderHistory(), null, false, 'click')
      return
    }
    state.mode = 'stats'
    var period = getPeriod()
    showBubble(GREETING[period] + '！让我看看数据…', null, false, 'click')
    // 先查余额：不足时提示，充足才显示数据
    fetch('/pet/balance/', { credentials: 'same-origin' })
      .then(function (r) { return r.json() })
      .then(function (b) {
        if (!state.bubbleShown) return
        if (b.ok && b.insufficient) {
          showBubble(
            '呜……我的余额不足了 (｡•́︿•̀｡)\n' +
            '当前余额：' + b.balance + ' ' + (b.currency || 'CNY') + '\n\n' +
            '去 <a href="https://platform.deepseek.com/top_up" target="_blank" style="color:#e0433f">DeepSeek 平台</a> 充值后，我就能继续陪你聊天啦~',
            null, true, 'click')
          return
        }
        fetchStatsIntoBubble(period)
      })
      .catch(function () {
        // 余额接口失败（如未配置 key）：不影响正常显示
        if (state.bubbleShown) fetchStatsIntoBubble(period)
      })
    resetBubbleTimer()
  }

  function fetchStatsIntoBubble(period) {
    fetch(statsUrl(), { credentials: 'same-origin' })
      .then(function (r) { return r.json() })
      .then(function (d) {
        if (!state.bubbleShown) return
        if (!d.ok) { showBubble('数据加载失败了呢……', null, false, 'click'); return }
        state.pageStats = d
        var as = d.article_stats
        var bs = d.blog_stats
        var lines = []
        if (d.logged_in) {
          lines.push('你好呀，' + d.username + '！' + pickOne(LINES[period]))
        } else {
          lines.push(GREETING[period] + '！我是博客的小鲸鱼娘 🐋')
          lines.push('你还没登录哦，登录后我可以记住你~')
          lines.push('👉 <a href="/login/" style="color:#e0433f">去登录</a>　<a href="/register/" style="color:#4a6bb8">去注册</a>')
        }
        lines.push('')
        if (as) {
          // 文章详情页：当前文章数据
          lines.push('📌 当前文章：' + as.title)
          lines.push('👤 作者：' + as.author)
          lines.push('👍 点赞 ' + as.up + '　👎 点踩 ' + as.down)
          lines.push('👀 阅读 ' + as.read + '　💬 评论 ' + as.comment)
          lines.push('')
          lines.push('（点我换台词，输入框问我问题~）')
        } else if (bs) {
          // 站点汇总
          lines.push('🏠 ' + (bs.site_title || bs.blog) + ' 站点数据：')
          lines.push('📝 文章 ' + bs.stats.total + ' 篇')
          lines.push('👀 总阅读 ' + bs.stats.read)
          lines.push('👍 总点赞 ' + bs.stats.up + '　👎 总点踩 ' + bs.stats.down)
          lines.push('💬 总评论 ' + bs.stats.comment)
          lines.push('')
          lines.push('（点我换台词，输入框问我问题~）')
        } else {
          // 全站
          lines.push('📊 博客全站数据：')
          lines.push('📝 文章 ' + d.stats.total + ' 篇')
          lines.push('👀 总阅读 ' + d.stats.read)
          lines.push('👍 总点赞 ' + d.stats.up + '　👎 总点踩 ' + d.stats.down)
          lines.push('💬 总评论 ' + d.stats.comment)
          lines.push('👥 博主 ' + d.blog_count + ' 位 · 🏷️ 标签 ' + d.tag_count + ' 个')
          lines.push('')
          lines.push('（点我换台词，输入框问我问题~）')
        }
        showBubble(lines.join('\n'), null, true, 'click')
      })
      .catch(function () {
        if (state.bubbleShown) showBubble('呜呜，数据请求失败了… (｡•́︿•̀｡)', null, false, 'click')
      })
    resetBubbleTimer()
  }

  /* ---------- 对话 ---------- */
  // 把用户消息和 AI 回复存入历史
  function pushHistory(role, text) {
    state.chatHistory.push({ role: role, text: text })
    if (state.chatHistory.length > CHAT_HISTORY_MAX) {
      state.chatHistory.shift()
    }
  }

  // 渲染历史对话文本（含角色标识）
  function renderHistory() {
    if (!state.chatHistory.length) return ''
    var lines = []
    state.chatHistory.forEach(function (m) {
      if (m.role === 'user') {
        lines.push('🧑 ' + m.text)
      } else {
        lines.push('🐋 ' + m.text)
      }
    })
    return lines.join('\n')
  }

  function sendChat() {
    var msg = chatInput.value.trim()
    if (!msg) return
    chatInput.value = ''
    state.mode = 'chat'
    pushHistory('user', msg)
    showBubble('让我想想……（检索站内知识库中）', null, false, 'click')
    fetch('/pet/chat/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ msg: msg }),
    })
      .then(function (r) { return r.json() })
      .then(function (d) {
        if (!state.bubbleShown) return
        if (!d.ok) { showBubble('出错了：' + (d.msg || '未知错误'), null, false, 'click'); return }
        var text = d.reply || '…'
        pushHistory('ai', text)
        // 显示最新回复 + 历史对话（输入框聚焦时不会自动消失）
        if (d.hits && d.hits.length) {
          showBubble(text + '\n\n—— 历史对话 ——\n' + renderHistory(), d.hits, false, 'click')
        } else {
          showBubble(text + '\n\n—— 历史对话 ——\n' + renderHistory(), null, false, 'click')
        }
      })
      .catch(function () {
        if (state.bubbleShown) showBubble('网络开小差了，稍后再试吧~', null, false, 'click')
      })
    resetBubbleTimer()
  }

  chatBtn.addEventListener('click', function (e) {
    e.stopPropagation()
    sendChat()
  })
  chatInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.stopPropagation()
      sendChat()
    }
  })
  chatInput.addEventListener('click', function (e) { e.stopPropagation() })
  bubble.addEventListener('click', function (e) { e.stopPropagation() })

  /* ---------- 悬浮显示当前页面信息 ---------- */
  var hoverTimer = null
  root.addEventListener('mouseenter', function () {
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null }
    hoverTimer = setTimeout(showPageInfo, 250)
  })
  root.addEventListener('mouseleave', function () {
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null }
    // 输入聚焦时不移除气泡（鼠标可能在气泡上打字）
    if (state.inputFocused) return
    if (state.bubbleShown && state.bubbleSource === 'hover') hideBubble()
  })

  /* 输入框聚焦/失焦：聚焦时暂停自动隐藏 */
  chatInput.addEventListener('focus', function () {
    state.inputFocused = true
    if (state.bubbleTimer) { clearTimeout(state.bubbleTimer); state.bubbleTimer = null }
  })
  chatInput.addEventListener('blur', function () {
    state.inputFocused = false
    if (state.bubbleShown) resetBubbleTimer()
  })

  /* 点击页面其他位置关闭气泡 */
  document.addEventListener('click', function (e) {
    if (!root.contains(e.target)) hideBubble()
  })

  loadPos()
})()
