loadPage = (url) ->
  $('.jqload-error').fadeOut ->
    $('.content').stop().fadeOut ->
      $('.loader').fadeIn()
      $('.content').load url + ' .content',
        (response, status, xhr) ->
          $('.loader').slideUp()
          if status is 'error'
            if xhr.status is 418
              document.location = url
            else
              $('.jqload-error').fadeIn()
          else if (xhr.getResponseHeader('Content-Type')?.lastIndexOf('text/html', 0) is -1)
            # if the response isn't HTML, jQuery fails silently
            # in that case, we ought to set the location manually
            document.location = url
          else
            elem = this
            $(elem).fadeIn()



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

