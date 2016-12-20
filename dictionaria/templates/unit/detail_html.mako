<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>

<%def name="sentences(obj=None, fmt='long')">
    <% obj = obj or ctx %>
    <ul id="sentences-${obj.pk}" class="unstyled">
        % for a in obj.sentence_assocs:
            <li>
                <blockquote style="margin-top: 5px;">
                ${h.link(request, a.sentence, label='%s %s:' % (_('Sentence'), a.sentence.id))}<br>
                % if a.description and fmt == 'long':
                    <p>${a.description}</p>
                % endif
                ${h.rendered_sentence(a.sentence, fmt=fmt)}
                % if a.sentence.alt_translation1:
                <div>
                    <span class="alt-translation translation">${a.sentence.alt_translation1}</span>
                    <span class="alt-translation">[${a.sentence.alt_translation_language1}]</span>
                </div>
                % endif
                    % if a.sentence.alt_translation2:
                        <div>
                            <span class="alt-translation translation">${a.sentence.alt_translation2}</span>
                            <span class="alt-translation">[${a.sentence.alt_translation_language2}]</span>
                        </div>
                    % endif
            % if a.sentence.audio:
            <div>
                ${u.cdstar.audio(a.sentence.audio)}
            </div>
            % endif
            % if (a.sentence.references or a.sentence.source) and fmt == 'long':
            Source: ${h.linked_references(request, a.sentence)|n} <span class="label">${a.sentence.source}</span>
            % endif
                    </blockquote>
            </li>
        % endfor
    </ul>
</%def>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        ${h.link(request, ctx.dictionary)} by ${h.linked_contributors(request, ctx.dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.dictionary.name, request.resource_url(ctx.dictionary, ext='md.html')))}
    </%util:well>
    % for file in ctx._files:
        % if file.mime_type.startswith('audio'):
            <p>
                ${u.cdstar.audio(file)}
            </p>
        % endif
    % endfor
    % for file in ctx._files:
        % if file.mime_type.startswith('image'):
            <div class="img-with-caption well">
                ${u.cdstar.linked_image(file)}
                ##<img src="${h.data_uri(request.file_ospath(file), file.mime_type)}" class="img-polaroid">
                % if file.jsondata.get('copyright'):
                    <p>© ${file.jsondata.get('copyright')}</p>
                % endif
            </div>
        % endif
    % endfor
</%def>

<h2>${ctx.label}: <span class="meanings-in-title">${' / '.join(u.split(m.name)[0] for m in ctx.meanings)}</span></h2>

<table class="table table-condensed table-nonfluid borderless">
    % if ctx.pos:
    <tr>
        <td><small>part of speech</small></td>
    <td>
        <span class="vocabulary">${ctx.pos}</span>
    </td>
    </tr>
    % endif
    % if ctx.counterparts:
        <tr>
            <td><small>comparison meanings</small></td>
            <td>
                <ul class="unstyled">
                % for c in ctx.counterparts:
                    <li>
                        ${h.link(request, c.valueset.parameter)}
                    </li>
                % endfor
                </ul>
            </td>
        </tr>
    % endif
    % for value in ctx.unitvalues:
    <tr>
        <td>${h.link(request, value.unitparameter)}</td>
        <td>
            <small>
                ${value}
                % if value.name:
                    (${value.name})
                % endif
            </small>
        </td>
    </tr>
    % endfor
% for _d in ctx.data:
    % if not _d.key.startswith('lang-'):
    <tr>
        <td><small>${_d.key}</small></td>
        <td>${_d.value}</td>
    </tr>
    % endif
% endfor
</table>

${'<ul class="unstyled">' if len(ctx.meanings) <= 1 else '<ol>'|n}
    % for m in ctx.meanings:
        <li>
            <ul class="unstyled">
                <li>
                    <strong>${m.name}</strong>
                ##% if m.gloss and m.name != m.gloss:
                ##    [${m.gloss}]
                ##% endif
                % if m.reverse and m.reverse != m.name:
                    Comparison meaning: <strong>${m.reverse}</strong>
                % endif
                    </li>
            % if m.alt_translation1:
                <li>
                    <span class="alt-translation">${m.alt_translation1} [${m.alt_translation_language1}]</span>
                </li>
            % endif
            % if m.alt_translation2:
                <li>
                    <span class="alt-translation">${m.alt_translation2} [${m.alt_translation_language2}]</span>
                </li>
            % endif
            % if m.semantic_domain_list:
                <li>
                    <ul class="inline semantic_domains_inline">
                        % for sd in m.semantic_domain_list:
                            <li><span class="vocabulary">${sd}</span></li>
                        % endfor
                    </ul>
                </li>
            % endif
                % if m.sentence_assocs:
                    <li>${sentences(m)}</li>
                % endif
            </ul>
        </li>
    % endfor
${'</ul>' if len(ctx.meanings) <= 1 else '</ol>'|n}

% if ctx.linked_from or ctx.links_to:
<h4>Related entries</h4>
<ul>
    % for w, desc in set(list(ctx.linked_from) + list(ctx.links_to)):
        <li>
            % if desc:
                <span>${desc}:</span>
            % endif
            <span style="margin-right: 10px">${h.link(request, w, title=w.name, label=w.label)|n}</span>
            <strong>${'; '.join(w.description_list)}</strong>
        </li>
    % endfor
</ul>
% endif
