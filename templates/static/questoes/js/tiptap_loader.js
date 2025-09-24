import { Editor } from 'https://esm.sh/@tiptap/core';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit';
import { Markdown } from 'https://esm.sh/tiptap-markdown';

// Anexa tudo ao objeto global 'window' para ser acessível no SCRIPT de inicialização
// A extensão 'Underline' foi removida, pois já está incluída no StarterKit.
window.TipTap = {
    Editor,
    StarterKit,
    Markdown,
};