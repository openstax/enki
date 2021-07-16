import * as path from "path";
import { digraph, attribute, Dot } from "ts-graphviz";
import { exportToFile } from "@ts-graphviz/node";
import { GIT_PDF_STEPS, GIT_WEB_STEPS, ARCHIVE_PDF_STEPS, ARCHIVE_GDOC_STEPS, ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD, Step } from './step-definitions'

const DIRS_TO_SKIP = new Set()
DIRS_TO_SKIP.add('book')

function ensure<T>(v: T | undefined | null, message?: string) {
    /* istanbul ignore if */
    if (!message) message = `BUG: value was expected to be truthy but instead was ${v}`
    /* istanbul ignore else */
    if (v) {
        return v
    } else {
        throw new Error(message)
    }
}

type Edge = {
    dirName: string
    from: string
    to: string
}

async function buildChart(steps: Step[], destFilename: string, additionalResource?: string) {
    const nodes: string[] = []
    const edges: Edge[] = []
    const prevOutputs = new Map<string, string>() // directory, stepName

    console.log('Generating image file:', destFilename)

    // Add the concourse resources as inputs
    if (additionalResource) {
        steps.unshift({name: 'Misc Resources', inputs: [], outputs: [additionalResource], env: {}})
    }

    steps.forEach(step => {
        nodes.push(step.name)
        step.inputs.forEach(dir => {
            if (DIRS_TO_SKIP.has(dir)) { return }
            const from = ensure(prevOutputs.get(dir), `Step '${step.name}' has an input directory of '${dir}' but no previous step has that as an output directory`)
            const to = step.name
            edges.push({dirName: dir, from, to})
        })
        step.outputs.forEach(dir => {
            if (DIRS_TO_SKIP.has(dir)) { return }
            prevOutputs.set(dir, step.name)
        })
    })

    const G = digraph("G", (g) => {
        const nodeMap = new Map<string, Dot>()
        nodes.forEach(n => nodeMap.set(n, g.node(n)))

        edges.forEach(({dirName, from, to}) => {
            g.edge([from,to], {
                [attribute.label]: dirName
            })
        });
      });
      
      
      await exportToFile(G, {
        format: "png",
        output: path.resolve(destFilename),
      });
}


(async function buildCharts() {
    await buildChart(GIT_PDF_STEPS, './graphs/git-pdf.png')
    await buildChart(GIT_WEB_STEPS, './graphs/git-web.png')
    await buildChart(ARCHIVE_PDF_STEPS, './graphs/archive-pdf.png')
    await buildChart(ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD, './graphs/archive-web.png', 's3-queue')
    await buildChart(ARCHIVE_GDOC_STEPS, './graphs/archive-gdocs.png')
})().then(null, console.error)