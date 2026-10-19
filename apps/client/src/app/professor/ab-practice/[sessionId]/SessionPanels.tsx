'use client';

import dynamic from 'next/dynamic';
import Image from 'next/image';
import type { RefObject } from 'react';
import {
  CheckCircle2,
  ImagePlus,
  Loader2,
  RefreshCw,
  Trash2,
  Users,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { API_URL, abPracticeApi } from '@/lib/api';
import { useImageFileSelection } from '@/hooks/useImageFileSelection';
import type {
  ABPracticeProgressResponse,
  ABPracticeSessionResponse,
} from '@/lib/types';

const QRCode = dynamic(() => import('react-qr-code'), { ssr: false });

type FileSelection = ReturnType<typeof useImageFileSelection>;
type RunAction = (
  action: () => Promise<unknown>,
  failureMessage: string,
) => Promise<boolean>;

interface RegistrationPanelProps {
  session: ABPracticeSessionResponse;
  progress: ABPracticeProgressResponse;
  sessionId: number;
  registrationOpen: boolean;
  busy: boolean;
  pairTitle: string;
  onPairTitleChange: (title: string) => void;
  imageA: FileSelection;
  imageB: FileSelection;
  imageARef: RefObject<HTMLInputElement | null>;
  imageBRef: RefObject<HTMLInputElement | null>;
  onAddPair: () => void;
  runAction: RunAction;
}

function assetUrl(path: string): string {
  return path.startsWith('http') ? path : `${API_URL.replace(/\/+$/, '')}${path}`;
}

function completionPercent(complete: number, total: number): number {
  return total > 0 ? Math.round((complete / total) * 100) : 0;
}

function ImageSelectionField({
  slot,
  selection,
  inputRef,
  disabled,
}: {
  slot: 'A' | 'B';
  selection: FileSelection;
  inputRef: RefObject<HTMLInputElement | null>;
  disabled: boolean;
}) {
  return (
    <label className="cursor-pointer space-y-2 rounded-lg border border-dashed p-3 text-center hover:border-primary">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => selection.selectFile(event.target.files?.[0] ?? null)}
      />
      <div className="relative aspect-[4/5] overflow-hidden rounded-md bg-muted">
        {selection.previewUrl ? (
          <Image
            unoptimized
            src={selection.previewUrl}
            alt={`선택한 이미지 ${slot} 미리보기`}
            fill
            className="object-contain"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <ImagePlus className="h-5 w-5" />
            <span className="text-xs">미리보기</span>
          </div>
        )}
      </div>
      <span className="block text-sm font-medium">이미지 {slot}</span>
      <span className="block truncate text-xs text-muted-foreground">
        {selection.file?.name ?? '파일 선택'}
      </span>
    </label>
  );
}

function RegisteredPairCard({
  pair,
  index,
  sessionId,
  registrationOpen,
  busy,
  runAction,
}: {
  pair: ABPracticeProgressResponse['pairs'][number];
  index: number;
  sessionId: number;
  registrationOpen: boolean;
  busy: boolean;
  runAction: RunAction;
}) {
  const handleDelete = () => {
    if (!window.confirm(`‘${pair.title}’ 항목을 삭제할까요?`)) return;
    void runAction(
      () => abPracticeApi.deleteProfessorPair(sessionId, pair.id),
      'A/B 테스트 항목을 삭제하지 못했습니다.',
    );
  };

  return (
    <Card className="overflow-hidden border-border/70 bg-card/80">
      <CardHeader className="flex flex-row items-start justify-between gap-2 p-3">
        <div className="min-w-0">
          <CardTitle className="text-sm">
            {pair.title}
            {!pair.complete ? (
              <span className="ml-1 text-xs font-normal text-amber-700">미완성</span>
            ) : null}
          </CardTitle>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {pair.submitter_name}
          </p>
        </div>
        {registrationOpen ? (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-destructive"
            disabled={busy}
            aria-label={`${pair.title} 삭제`}
            onClick={handleDelete}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        ) : null}
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2 p-3 pt-0">
        {(['a', 'b'] as const).map((slot) => {
          const imageUrl = slot === 'a' ? pair.image_a_url : pair.image_b_url;
          const slotLabel = `이미지 ${slot.toUpperCase()}`;
          return (
            <div key={slot} className="space-y-1">
              <div className="relative aspect-[4/5] overflow-hidden rounded border bg-muted">
                {imageUrl ? (
                  <Image
                    unoptimized
                    src={assetUrl(imageUrl)}
                    alt={`A/B 테스트 항목 ${index + 1} ${slotLabel}`}
                    fill
                    className="object-contain"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                    이미지 없음
                  </div>
                )}
              </div>
              {registrationOpen ? (
                <label
                  title={`${slotLabel} ${imageUrl ? '교체' : '업로드'}`}
                  className="flex cursor-pointer justify-center text-xs text-primary underline underline-offset-4"
                >
                  {imageUrl ? (
                    <>
                      <RefreshCw className="h-4 w-4" />
                      <span className="sr-only">{slotLabel} 교체</span>
                    </>
                  ) : (
                    '업로드'
                  )}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="sr-only"
                    disabled={busy}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file)
                        void runAction(
                          () => abPracticeApi.replaceProfessorImage(sessionId, pair.id, slot, file),
                          '이미지를 교체하지 못했습니다.',
                        );
                    }}
                  />
                </label>
              ) : (
                <div className="text-center text-xs font-medium">{slot.toUpperCase()}</div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function RegistrationPanel(props: RegistrationPanelProps) {
  const {
    session,
    progress,
    sessionId,
    registrationOpen,
    busy,
    pairTitle,
    onPairTitleChange,
    imageA,
    imageB,
    imageARef,
    imageBRef,
    onAddPair,
    runAction,
  } = props;
  const completePairCount = progress.pairs.filter((pair) => pair.complete).length;

  return (
    <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
      <div className="space-y-6">
        <Card className="glass-card min-h-[360px] rounded-xl animate-entrance border-0 shadow-md">
          <CardHeader>
            <CardTitle>A/B 테스트 항목 등록 QR</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center gap-4 text-center">
            {registrationOpen ? (
              <>
                <div className="rounded-xl bg-white p-4">
                  <QRCode value={session.upload_url} size={208} />
                </div>
                <a
                  className="break-all text-sm text-primary underline underline-offset-4"
                  href={session.upload_url}
                >
                  {session.upload_url}
                </a>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
            {session.status === 'setup'
                  ? '등록 개시 후 QR이 표시됩니다. 등록을 다시 열어 항목을 이어서 등록할 수 있습니다.'
                  : 'A/B 테스트 항목 등록이 종료되었습니다.'}
              </div>
            )}
          </CardContent>
        </Card>
        {registrationOpen ? (
          <Card className="glass-card rounded-xl border-0 shadow-md">
            <CardHeader>
              <CardTitle>관리자 직접 등록</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-muted-foreground">
                A와 B 이미지를 함께 선택해 새 A/B 테스트 항목으로 등록합니다.
              </p>
              <div className="space-y-2">
                <label htmlFor="ab-professor-pair-title" className="text-sm font-medium">
                  항목 제목
                </label>
                <Input
                  id="ab-professor-pair-title"
                  maxLength={200}
                  value={pairTitle}
                  onChange={(event) => onPairTitleChange(event.target.value)}
                  placeholder="예: 정리된 공간 메시지"
                  disabled={busy}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <ImageSelectionField
                  slot="A"
                  selection={imageA}
                  inputRef={imageARef}
                  disabled={busy}
                />
                <ImageSelectionField
                  slot="B"
                  selection={imageB}
                  inputRef={imageBRef}
                  disabled={busy}
                />
              </div>
              <Button
                className="w-full"
                disabled={busy || !pairTitle.trim() || !imageA.file || !imageB.file}
                onClick={onAddPair}
              >
                {busy ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    등록 중...
                  </>
                ) : (
                  'A/B 테스트 항목 등록'
                )}
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>

      <Card className="glass-card min-h-[420px] rounded-xl animate-entrance border-0 shadow-md lg:min-h-[500px]">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>등록된 A/B 테스트 항목</CardTitle>
            <div className="space-y-2 text-right">
              <div className="text-sm font-medium">
                전체 {progress.pairs.length}개 · 완성 {completePairCount}개
              </div>
              <Progress
                value={completionPercent(completePairCount, progress.pairs.length)}
                className="h-3 w-56"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {progress.pairs.length === 0 ? (
            <div className="rounded-md border border-dashed py-12 text-center text-sm text-muted-foreground">
              등록된 A/B 테스트 항목이 없습니다.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {progress.pairs.map((pair, index) => (
                <RegisteredPairCard
                  key={pair.id}
                  pair={pair}
                  index={index}
                  sessionId={sessionId}
                  registrationOpen={registrationOpen}
                  busy={busy}
                  runAction={runAction}
                />
              ))}
            </div>
          )}
          {registrationOpen && progress.pairs.length > 0 ? (
            <p className="mt-4 text-xs text-muted-foreground">
              등록된 항목은 세션 생성자는 모두 수정·삭제할 수 있고, QR 등록자는 본인이 올린 항목만 수정·삭제할 수 있습니다.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

interface VotingPanelProps {
  session: ABPracticeSessionResponse;
  progress: ABPracticeProgressResponse;
  sessionId: number;
  hasCompletePair: boolean;
  votedPercent: number;
  busy: boolean;
  runAction: RunAction;
}

export function VotingPanel({
  session,
  progress,
  sessionId,
  hasCompletePair,
  votedPercent,
  busy,
  runAction,
}: VotingPanelProps) {
  return (
    <div className="grid flex-1 gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
      <Card className="glass-card min-h-[420px] rounded-xl animate-entrance border-0 shadow-md lg:min-h-[500px]">
        <CardHeader>
          <CardTitle>학생 A/B 테스트 참여 QR</CardTitle>
        </CardHeader>
        <CardContent className="flex h-full flex-col items-center justify-center gap-4 text-center">
          {session.status === 'voting_open' ? (
            <>
              <div className="rounded-xl bg-white p-4">
                <QRCode value={session.test_url} size={280} />
              </div>
              <a
                className="break-all text-xs text-muted-foreground underline underline-offset-4"
                href={session.test_url}
              >
                {session.test_url}
              </a>
              <p className="text-sm text-muted-foreground">
                선택하면 바로 다음 A/B 테스트 항목으로 이동합니다.
              </p>
            </>
          ) : (
            <div className="space-y-2 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">
                {session.status === 'ended' ? '테스트가 종료되었습니다.' : '테스트 진행 대기 중입니다.'}
              </p>
              <p>
                {session.status === 'ended'
                  ? '참여 현황은 오른쪽에서 확인할 수 있습니다.'
                  : hasCompletePair
                    ? '테스트 진행을 누르면 참여 QR이 표시됩니다.'
                    : '완성된 A/B 테스트 항목을 하나 이상 등록해 주세요.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="glass-card min-h-[420px] rounded-xl animate-entrance border-0 shadow-md lg:min-h-[500px]">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              투표 참여 현황
            </CardTitle>
            <div className="space-y-2 text-right">
              <div className="text-sm font-medium">참여 {progress.total_students}명</div>
              <Progress value={votedPercent} className="h-3 w-56" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {progress.students.length ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
              {progress.students.map((student) => {
                const displayName = student.serial_number
                  ? `${student.serial_number}. ${student.student_name}`
                  : student.student_name;
                const resetResponses = () =>
                  student.participant_id !== null
                    ? abPracticeApi.resetAnonymousParticipantResponses(sessionId, student.participant_id)
                    : student.student_user_id !== null
                      ? abPracticeApi.resetStudentResponses(sessionId, student.student_user_id)
                      : Promise.resolve();

                return (
                  <div
                    key={student.participant_id ?? student.student_user_id ?? displayName}
                    className={`rounded-md border px-2.5 py-2 text-center ${student.completed ? 'border-emerald-700/30 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200' : 'border-border/70 bg-card/80'}`}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <div className="min-w-0 truncate text-sm font-medium" title={displayName}>
                        {displayName}
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        disabled={busy}
                        aria-label={`${displayName}의 투표 기록 삭제 후 재참여 허용`}
                        title="투표 기록 삭제 후 재참여 허용"
                        onClick={() =>
                          void runAction(resetResponses, '투표 기록을 초기화하지 못했습니다.')
                        }
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="mt-1 text-xs">
                      {student.completed ? (
                        <span className="inline-flex items-center gap-1">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          완료
                        </span>
                      ) : session.status === 'voting_open' ? (
                        `${student.answered_count}/${student.total_pairs} 선택`
                      ) : (
                        '미완료'
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              아직 투표에 참여한 사용자가 없습니다.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
