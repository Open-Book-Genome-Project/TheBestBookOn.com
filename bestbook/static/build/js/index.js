var api_url = '//' + window.location.host + '/api';

$( function() {

  $.support.cors = true

  requests = {
    get: function(url, callback) {
      $.get(url, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    post: function(url, data, callback) {
      $.post(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    put: function(url, data, callback) {
      $.put(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },
  };

  var formData = {};

  var candidates = [];
  var candidateIndex = 0;

  function selectCandidateWork(title, image, olid) {
    // Store candidate data
    var candidate = {
      title: title,
      image: image,
      olid: olid
    };
    candidates.push(candidate);

    // Create list item and append to list
    var listItem = `
      <li id="candidate-list-item${++candidateIndex}">
        <a href="https://openlibrary.org${candidate.olid}" target="_blank">
          <img src="${candidate.image}">
          <span class="book-title">${candidate.title}</span>
        </a>
        <span id="list-delete${candidateIndex}" class="list-delete">
        X
        </span>
      </li>`;

    $('#candidate-list').append(listItem);

    // Add delete listener
    $(`#list-delete${candidateIndex}`).on('click', function() {
      deleteListItem($(this).parent());
    });

    // Add olid to list item
    $(`#candidate-list-item${candidateIndex}`).attr('data-olid', candidate.olid)

    // Clear input and remove required attribute
    $('#candidate').val('');
    $('#candidate').removeAttr('required');
  }

  var deleteListItem = function($selector) {
    // Find and remove item from candidates list
    var olid = $selector.attr('data-olid')
    var index = -1
    for(var i = 0; i < candidates.length && index === -1; ++i) {
      if(candidates[i].olid === olid) {
        index = i;
      }
    }

    candidates.splice(index, 1);

    // Remove list item from UI
    $selector.remove()

    // If candidates list is empty, add 'required' attribute to candidate text box
    if(candidates.length === 0) {
      $('#candidate').attr('required', true)
    }
  }


  /* This is the main function which registers a <input class="ui-widget">
     as an autocomplete
  */
  var bind_autocomplete = function(self, selector, callback) {
    $(selector).autocomplete({
      source: function (request, response) {
          $.ajax(callback(request, response));
      },
      minLength: 2,
      focus: function (event, ui) {
        $(event.target).val(ui.item.label);
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);
        return false;
      },
      select: function (event, ui) {
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);

        var targetId = event.target.id;
        switch(targetId) {
          case 'topic':
            formData[targetId] = ui.item.label;
            break;
          case 'candidate':
            selectCandidateWork(ui.item.label, ui.item.img, ui.item.value);
            break;
          default:
            formData[targetId] = ui.item.value;
        }

        return false;
      }
    }).data("ui-autocomplete")._renderItem = function (ul, item) {
      /* Renders how the data appears in the autocomplete menu */
      // NOTE: I think we only want to do this for search_books (and not search_topics)
      return $("<li />")
        .data( "ui-autocomplete-item", item)
        .append("<a class='book-result'><img src='" + item.img + "' />" + item.label + "</a>")
        .appendTo(ul);
    };
  }

  var search_books = function(request, response) {
    return {
      url: 'https://openlibrary.org/search.json?limit=10&q=' + request.term,
      success: function(resp) {
        var entities = $.map(resp.docs, function(book) {
          return {
            label: book.title,
            value: book.key,
            img: 'https://covers.openlibrary.org/b/olid/' + book.cover_edition_key + '-S.jpg'
          }
        });
        response(entities);
      }
    }
  };

  var search_topics = function(request, response) {
    return {
      url: api_url + '/topics?query=' + request.term + '&field=name&action=search',
      success: function(resp) {
        var entities = $.map(resp.topics, function(topic) {
          return {
            label: topic.name,
            value: topic.id,
	    img: ''
          }
        });

        entities.push({
          label: $('.book-topic-selector').autocomplete('instance').term,
          value: '',
          img: '',
          lastItem: true
        });
        response(entities);
      }
    }
  };

  var suggest_topic = function(topic) {
    $.ajax({
      type: 'POST',
      url: '/api/topics',
      contentType: 'application/json',
      data: JSON.stringify(topic)
    });
  }

  if ($('#recommendations-form').length) {
    $(this).on('submit', function(event) {
      event.preventDefault()

      formData.candidates = [];
      for(var i = 0; i < candidates.length; ++i) {
        formData.candidates.push(candidates[i].olid)
      }
      // TODO: Handle success and failure
      $.ajax({
        type: 'POST',
        url: '/submit',
        data: formData,
      })
    })
  }

  if ($(".book-winner-selector").length) { bind_autocomplete(self, ".book-winner-selector", search_books); }
  if ($("#candidate").length) { bind_autocomplete(self, "#candidate", search_books); }
  if ($(".book-topic-selector").length) {
    bind_autocomplete(self, ".book-topic-selector", search_topics);

    var render = $('.book-topic-selector').autocomplete('instance')._renderMenu;

    $('.book-topic-selector').autocomplete('instance')._renderMenu = function(ul, items) {
      render.call(this, ul, items);

      $('#add-topic').on('click', function(event) {
        event.preventDefault();

        var topic = {
          topic: $('.book-topic-selector').autocomplete('instance').term
        }

        suggest_topic(topic);
      });
    }


    var renderItem = $('.book-topic-selector').autocomplete('instance')._renderItem;

    $(".book-topic-selector").autocomplete('instance')._renderItem = function(ul, item) {
      if(item.lastItem) {
        return $("<li />").append(
          'Topic not found. Add <a id="add-topic" href="javascript:;">' +
          $(".book-topic-selector").autocomplete('instance').term + '?</a>'
        ).appendTo(ul);
      }
      return renderItem.call(this, ul, item);
    }
  }
});

/* Admin functions: */
function approveRequest(requestId) {
  let payload = { approved: true }

  $.ajax({
    type: 'POST',
    url: `/api/requests/${requestId}`,
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(msg) {
      updateButtonGroup(requestId, msg);
    }
  })

}

function rejectRequest(requestId) {
  $.ajax({
    type: 'DELETE',
    url: `/api/requests/${requestId}`,
    success: function(msg) {
      updateButtonGroup(requestId, msg);
    }
  })
}

function approveRecommendation(recommendationId) {
  let payload = { approved: true }

  $.ajax({
    type: 'POST',
    url: `/api/recommendations/${recommendationId}`,
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(msg) {
      updateButtonGroup(recommendationId, msg);
    }
  })
}

function rejectRecommendation(recommendationId) {
  $.ajax({
    type: 'DELETE',
    url: `/api/recommendations/${recommendationId}`,
    success: function(msg) {
      updateButtonGroup(recommendationId, msg);
    }
  })
}

function updateButtonGroup(id, msg) {
  let div = $(`#button-group-${id}`)
  div.children().hide()
  div.append(`<p>${msg}</p>`)
}
