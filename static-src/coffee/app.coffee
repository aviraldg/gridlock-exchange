loadPage = (url) ->
  $('.content').stop().fadeOut().load(url + ' .content',
    (response, status, xhr) ->
      # if the response isn't HTML, jQuery fails silently
      # in that case, we ought to set the location manually
      if (xhr.getResponseHeader('Content-Type')?.lastIndexOf('text/html', 0) is -1) or status isnt 'success'
        document.location = url
      else
        $(this).fadeIn()
        initInfiniteScroll()
  )

initInfiniteScroll = ->
  # Infinite scroll
  # TODO Should we change the URL here?
  $('.content').infinitescroll
    navSelector: '.pager'
    nextSelector: '.load-more'
    itemSelector: '.content article'

loadSearchTimeout = null
prevQuery = ''

loadSearch = (query) ->
  if loadSearchTimeout
    clearTimeout loadSearchTimeout

  unless query is prevQuery or not query.trim()
    loadSearchTimeout = setTimeout ->
      if query
        url = '/item?q='+encodeURIComponent(query)
      else
        url = '/item'

      loadPage url
      history.replaceState {'url': url}, '', url
    , 1000
    prevQuery = query

$ ->
  $('select').chosen() # Initialize Chosen (for better select widgets)

  # OPA emulation (makes app appear snappier)
  if history.pushState
    $('body').on 'click', 'a:not([no-jqload])', (e) ->
      history.pushState {'url': this.href}, '', this.href
      loadPage(this.href)
      e.preventDefault()

    originalURL = null

    $(window).on 'popstate', (e) ->
      url = e.originalEvent.state?.url
      unless url
        unless originalURL
          originalURL = location.href
        else
          loadPage originalURL
      else
        loadPage url
      null

    # Load search results in background as user types
    $('.search-query').on 'keyup', ->
      loadSearch this.value

    initInfiniteScroll()

