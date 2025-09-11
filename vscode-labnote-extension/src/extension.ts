import * as vscode from 'vscode';
// node-fetch v2는 CommonJS 모듈이므로 require 구문을 사용하는 것이 가장 안정적입니다.
const fetch = require('node-fetch');

// **개선점**: API 응답 타입을 명확하게 정의하여 코드 안정성을 높입니다.
interface ApiResponse {
    response: string;
    sources?: string[];
}

export function activate(context: vscode.ExtensionContext) {

    // **개선점**: 확장 프로그램의 상태를 알려주는 출력 채널을 생성합니다.
    // 이를 통해 사용자는 참고 자료(sources)나 디버깅 정보를 확인할 수 있습니다.
    const outputChannel = vscode.window.createOutputChannel("LabNote AI");
    outputChannel.appendLine('LabNote AI extension is now active.');

    let disposable = vscode.commands.registerCommand('labnote.ai.generate', async () => {

        const userInput = await vscode.window.showInputBox({
            prompt: '생성할 랩노트의 내용을 입력하세요.',
            placeHolder: '예: DH5a Transformation 프로토콜 알려줘'
        });

        if (!userInput) {
            vscode.window.showInformationMessage('입력이 취소되었습니다.');
            return;
        }

        // **개선점**: withProgress를 사용하여 사용자에게 명확한 피드백을 제공합니다.
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "LabNote AI가 작동 중입니다...",
            cancellable: true // 사용자가 작업을 취소할 수 있도록 설정
        }, async (progress, token) => {

            // 작업 취소 리스너
            token.onCancellationRequested(() => {
                outputChannel.appendLine("사용자가 작업을 취소했습니다.");
            });

            progress.report({ increment: 10, message: "백엔드 서버에 요청을 보냅니다..." });
            outputChannel.appendLine(`[Request] 사용자 쿼리: "${userInput}"`);


            try {
                const response = await fetch('https://run-execution-1dorfxqbb6kk-run-exec-8000.seoul.oracle-cluster.vessl.ai/generate_labnote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: userInput }),
                    // **개선점**: 긴 응답을 대비하여 타임아웃을 넉넉하게 설정합니다.
                    timeout: 60000 // 60초
                });
                
                if (token.isCancellationRequested) return;
                progress.report({ increment: 40, message: "AI가 응답을 생성 중입니다..." });


                if (!response.ok) {
                    const errorBody = await response.text();
                    throw new Error(`HTTP Error: ${response.status} ${response.statusText}\n${errorBody}`);
                }

                const data = await response.json() as ApiResponse;

                if (token.isCancellationRequested) return;
                progress.report({ increment: 90, message: "결과를 표시합니다..." });


                // **개선점**: AI가 생성한 마크다운을 새 문서 탭에 바로 표시합니다.
                const doc = await vscode.workspace.openTextDocument({
                    content: data.response,
                    language: 'markdown'
                });
                await vscode.window.showTextDocument(doc, { preview: false });

                // 참고 자료는 출력 채널에 기록합니다.
                if (data.sources && data.sources.length > 0) {
                    outputChannel.appendLine(`[Response] 생성 완료. 참고 자료: ${data.sources.join(', ')}`);
                } else {
                    outputChannel.appendLine(`[Response] 생성 완료. 참고 자료 없음.`);
                }
                outputChannel.show(true); // 사용자에게 출력 채널을 보여줍니다.


            } catch (error: any) {
                // **개선점**: 에러 메시지를 사용자 친화적으로 표시하고, 자세한 내용은 출력 채널에 기록합니다.
                vscode.window.showErrorMessage('LabNote AI 생성 중 오류가 발생했습니다. 자세한 내용은 출력 채널을 확인하세요.');
                outputChannel.appendLine(`[ERROR] ${error.message}`);
                outputChannel.show(true);
            }
        });
    });

    context.subscriptions.push(disposable);
}

// 확장 프로그램이 비활성화될 때 호출됩니다.
export function deactivate() {}

